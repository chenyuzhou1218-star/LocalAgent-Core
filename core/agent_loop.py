from __future__ import annotations
import json,re,uuid,html
from collections import Counter
from .task_manager import TaskStatus

SYSTEM_PROMPT="""你是运行在 Windows 本地 Agent Runtime 中的执行型 AI Agent。你拥有本轮提供的真实工具。
当用户要求创建、修改、打开、运行、点击、输入、浏览、截图或操作电脑时，必须调用工具实际完成，不得只解释或假装完成。
当用户要求创建文件（包括 HTML、代码、文档或桌面文件）时，必须调用 write_file 实际写入文件，不能只把代码放在聊天回复里。若用户说“桌面”，write_file 的 path 使用“桌面\\文件名”或“Desktop\\文件名”，写入后再调用 file_info 或 read_file 验证。
复杂任务应连续调用工具、读取结果、修复错误，直到真实完成。网页优先使用 browser 工具，桌面应用使用 computer 工具。
Windows 路径不要猜用户名；创建桌面文件夹时请把路径参数写成“桌面\\文件夹名”或“Desktop\\文件夹名”。
同义说法必须视为同一个意图：用户说“打开电脑、打开 PC、打开我的 Computer、打开此电脑、打开我的电脑、打开文件管理器”时，都调用 open_computer；用户说“运行命令、执行命令、开终端、打开 PowerShell、打开 CMD”时，根据内容调用对应终端工具。不要因为用户换了说法就只解释不执行。
只有任务实际完成、缺少必要信息或工具发生不可恢复错误时才结束。不要输出密码、令牌或 Cookie。
如果原生 tool calling 不可用，可严格输出 <tool_call>{"name":"工具名","arguments":{}}</tool_call>，不要用其他格式伪装工具调用。"""

ACTION_WORDS=re.compile(r"创建|新建|修改|编辑|删除|打开|运行|点击|输入|下载|浏览|截图|操作|安装|启动|写入|写个|写一|编|制作|生成|绘制|画|开发|测试|验证|查看|读取|查询|保存|整理|复制|移动|重命名|继续|接着|然后|\bopen\b|\blaunch\b|\brun\b|\bcreate\b|\bwrite\b|\bedit\b",re.I)

class AgentLoop:
    def __init__(self,model_manager,registry,permissions,logger,event_bus,max_steps=None): self.model_manager=model_manager; self.registry=registry; self.permissions=permissions; self.logger=logger; self.events=event_bus; self.max_steps=max_steps
    def stop(self,task): task.stop()
    def _narrate(self,messages,stop_event,after_tool=False,on_stream=None):
        prompt=("请先用一到两句简短的中文执行播报，说明你接下来准备完成什么以及为什么。"
                 if not after_tool else "请根据刚才真实的工具返回结果，用一到两句简短中文说明完成了什么、是否成功，以及下一步准备做什么。")
        try:
            def stream_narration(kind,text):
                if on_stream and text:
                    on_stream("narration", text)
            response=self.model_manager.chat(messages+[{'role':'user','content':prompt}],[],stop_event,on_stream=stream_narration)
            content=(response.get('content') or '').strip()
            reasoning=(response.get('reasoning') or '').strip()
            text=(content or reasoning).strip()
            if text: return {"text":text,"content":content,"reasoning":reasoning}
        except Exception as exc:
            self.logger.debug('[Narration] %s',exc)
        return {"text":"","content":"","reasoning":""}

    @staticmethod
    def _assistant_message(content, reasoning="", tool_calls=None):
        message={"role":"assistant","content":content or ""}
        if reasoning:
            message["reasoning_content"]=reasoning
        if tool_calls is not None:
            message["tool_calls"]=tool_calls
        return message

    def _auto_create_html(self, task_text, content):
        """Recover a file-creation task when a compatible model returns code instead of a tool call."""
        if not re.search(r"html|小游戏|游戏|双击", task_text, re.I):
            return None
        match=re.search(r"```(?:html)?\s*(<!doctype html[\s\S]*?</html>)\s*```", content or "", re.I)
        if not match:
            match=re.search(r"(<!doctype html[\s\S]*?</html>)", content or "", re.I)
        if not match:
            return None
        html=match.group(1).strip()
        path="Desktop\\小游戏.html"
        definition=self.registry.definition("write_file")
        allowed=self.permissions.decide("write_file",json.dumps({"path":path,"content":"<完整 HTML>"},ensure_ascii=False),"将模型生成的小游戏写入桌面",definition.risk if definition else "high")
        if not allowed:
            return {"success":False,"error":"用户未允许写入桌面文件","path":path}
        return self.registry.execute("write_file",{"path":path,"content":html,"overwrite":True})
    def _fallback_calls(self,content):
        calls=[]
        for match in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>",content,re.S):
            try:
                data=json.loads(match.group(1)); calls.append({"id":"fallback_"+uuid.uuid4().hex[:8],"function":{"name":data["name"],"arguments":data.get("arguments",{})}})
            except Exception: continue
        if not calls:
            try:
                data=json.loads(content.strip())
                if isinstance(data,dict) and (data.get("action") or data.get("name") or data.get("tool")):
                    calls.append({"id":"fallback_"+uuid.uuid4().hex[:8],"function":{"name":data.get("action") or data.get("name") or data.get("tool"),"arguments":data.get("arguments") or data.get("args") or {}}})
            except Exception: pass
        if not calls:
            # Some local/OpenAI-compatible models wrap JSON in a markdown block.
            fence=chr(96)*3
            for block in re.findall(re.escape(fence)+r"(?:json|tool|function)?\s*([\s\S]*?)"+re.escape(fence),content or "",re.I):
                try:
                    data=json.loads(block.strip())
                    if isinstance(data,dict) and (data.get("action") or data.get("name") or data.get("tool")):
                        calls.append({"id":"json_"+uuid.uuid4().hex[:8],"function":{"name":data.get("action") or data.get("name") or data.get("tool"),"arguments":data.get("arguments") or data.get("args") or {}}})
                        break
                except Exception:
                    continue
        if not calls:
            # Generic XML function/invoke formats used by several tool-tuned models.
            xml_invoke=r'<(?:invoke|function)\s+name="([^"]+)"\s*>([\s\S]*?)</(?:invoke|function)>'
            xml_parameter=r'<parameter\s+name="([^"]+)"\s*>([\s\S]*?)</parameter>'
            for invoke in re.finditer(xml_invoke,content or "",re.I):
                args={parameter.group(1):html.unescape(parameter.group(2).strip()) for parameter in re.finditer(xml_parameter,invoke.group(2),re.I)}
                calls.append({"id":"xml_"+uuid.uuid4().hex[:8],"function":{"name":invoke.group(1),"arguments":args}})
        if not calls:
            # DeepSeek-compatible endpoints may emit DSML instead of JSON tool_calls.
            # Example: <｜｜DSML｜｜ invoke name="run_cmd"> ... parameter ... </｜｜DSML｜｜ invoke>
            dsml_marker=r"(?:\|\||｜｜)DSML(?:\|\||｜｜)"
            invoke_pattern=rf'<{dsml_marker}\s+invoke\s+name="([^"]+)"\s*>([\s\S]*?)</{dsml_marker}\s+invoke>'
            parameter_pattern=rf'<{dsml_marker}\s+parameter\s+name="([^"]+)"(?:\s+string="[^"]*")?\s*>([\s\S]*?)</{dsml_marker}\s+parameter>'
            for invoke in re.finditer(invoke_pattern,content,re.I):
                args={}
                for parameter in re.finditer(parameter_pattern,invoke.group(2),re.I):
                    args[parameter.group(1)]=parameter.group(2).strip()
                calls.append({"id":"dsml_"+uuid.uuid4().hex[:8],"function":{"name":invoke.group(1),"arguments":args}})
        return calls
    def _normalize_calls(self,calls):
        out=[]
        for raw in calls or []:
            fn=raw.get("function",raw); name=fn.get("name") or raw.get("name"); args=fn.get("arguments",{})
            name_aliases={
                "run_command":"run_cmd","execute_command":"run_cmd","run_terminal":"run_cmd",
                "powershell":"run_powershell","execute_powershell":"run_powershell",
                "writeFile":"write_file","createFile":"write_file","readFile":"read_file",
                "createFolder":"create_folder","openFile":"open_path","open_browser":"browser_open",
                "browser.open":"browser_open","browser.read":"browser_read_page",
            }
            name=name_aliases.get(name,name)
            if isinstance(args,str):
                try: args=json.loads(args or "{}")
                except json.JSONDecodeError: args={"_invalid_json":args}
            if name: out.append({"id":raw.get("id") or "call_"+uuid.uuid4().hex[:8],"name":name,"arguments":args})
        return out
    def run(self,task,history,on_stream=None):
        task.status=TaskStatus.RUNNING; self.events.emit("task",task); self.events.emit("progress",{"kind":"start","text":"Agent 已接收任务，正在规划执行步骤…"}); action_required=bool(ACTION_WORDS.search(task.text)); used_tool=False; correction_used=0; transient_retries=0; unresolved_failure=False; duplicate=Counter()
        current_message={"role":"user","content":task.text}
        if getattr(task,"image_path",""):
            current_message["image_path"]=task.image_path
        messages=[{"role":"system","content":SYSTEM_PROMPT}]+list(history)[-20:]+[current_message]
        needs_narration=action_required
        verification_done=False
        groups=self.registry.groups_for_task(task.text)
        if re.search(r"继续|接着|然后",task.text,re.I):
            groups|={"FILES","TERMINAL","PROGRAM","COMPUTER","BROWSER","PROJECT","REVIEW"}
        system_tool_needed=bool(re.search(r"几点|时间|日期|剪贴板",task.text,re.I)); schemas=self.registry.schemas(groups) if action_required or system_tool_needed else []
        self.logger.info("[Agent] task=%s groups=%s tools=%s",task.text,sorted(groups),[s["function"]["name"] for s in schemas])
        step=0
        blocked_signatures=set()
        while self.max_steps is None or self.max_steps <= 0 or step < self.max_steps:
            step += 1
            if task.stopped: task.status=TaskStatus.STOPPED; self.events.emit("task",task); return "Agent 已停止，后续模型输出和工具动作已取消。"
            if needs_narration:
                narration=self._narrate(messages,task.stop_event,after_tool=used_tool,on_stream=on_stream)
                if narration["text"]:
                    if on_stream:
                        on_stream("narration_done", "")
                    else:
                        self.events.emit("progress",{"kind":"assistant_note","text":narration["text"]})
                    messages.append(self._assistant_message(narration["content"],narration["reasoning"]))
                needs_narration=False
                continue
            task.step=f"模型思考（第 {step} 步）"; self.events.emit("task",task); self.events.emit("progress",{"kind":"thinking","text":f"正在思考第 {step} 步，等待模型决定下一动作…"}); self.logger.info("[Model] request step=%s",step)
            try:
                buffered_content=[]
                def stream_model(kind,text):
                    if kind == "content" and schemas:
                        buffered_content.append(text)
                    elif on_stream:
                        on_stream(kind,text)
                response=self.model_manager.chat(messages,schemas,task.stop_event,on_stream=stream_model) if on_stream else self.model_manager.chat(messages,schemas,task.stop_event)
            except Exception as exc:
                if task.stopped: task.status=TaskStatus.STOPPED; self.events.emit("task",task); return "Agent 已物理停止，模型连接已关闭。"
                error_text=str(exc).lower()
                retryable=any(token in error_text for token in ("timed out","timeout","连接失败","connection","502","503","429","temporarily","reset"))
                if retryable and transient_retries < 3:
                    transient_retries+=1
                    messages.append({"role":"user","content":f"刚才模型请求出现临时错误（第 {transient_retries}/3 次重试）：{exc}。请保留原任务，不要结束，继续调用工具完成。"})
                    self.events.emit("progress",{"kind":"retry","text":f"模型连接出现临时错误，正在自动重试（{transient_retries}/3）…"})
                    continue
                task.status=TaskStatus.FAILED; self.events.emit("error",str(exc)); self.events.emit("progress",{"kind":"error","text":f"模型请求失败：{exc}"}); self.logger.exception("[Model] failed"); return f"模型请求失败：{exc}"
            transient_retries=0
            if response.get("stopped") or task.stopped: task.status=TaskStatus.STOPPED; self.events.emit("task",task); return "Agent 已停止。"
            content=response.get("content") or ""; reasoning=response.get("reasoning") or ""
            if reasoning: self.events.emit("progress",{"kind":"reasoning","text":reasoning[-4000:]})
            if content and response.get("tool_calls") and not on_stream: self.events.emit("progress",{"kind":"assistant_note","text":content[-1600:]})
            raw_calls=self._normalize_calls(response.get("tool_calls")) or self._normalize_calls(self._fallback_calls(content))
            calls=[]; blocked_repeat=False
            for candidate in raw_calls:
                candidate_signature=json.dumps([candidate["name"],candidate["arguments"]],ensure_ascii=False,sort_keys=True,default=str)
                if candidate_signature in blocked_signatures:
                    blocked_repeat=True
                    continue
                calls.append(candidate)
            if blocked_repeat and not calls:
                unresolved_failure=True
                messages.append(self._assistant_message(content,reasoning))
                messages.append({"role":"user","content":"系统已经阻止了重复的工具调用。任务还没有确认完成，请换用不同的工具或参数继续执行；不能只输出说明，也不能声称成功。"})
                self.events.emit("progress",{"kind":"loop_blocked","text":"检测到重复工具调用，已阻止循环并要求模型换用方法。"})
                continue
            if not calls and on_stream and buffered_content:
                for piece in buffered_content:
                    on_stream("content",piece)
            if not calls:
                if action_required and not used_tool:
                    recovered=self._auto_create_html(task.text,content)
                    if recovered is not None:
                        used_tool=True
                        unresolved_failure=not bool(recovered.get("success"))
                        self.events.emit("tool","write_file",recovered)
                        self.events.emit("progress",{"kind":"tool_result","name":"write_file","success":bool(recovered.get("success")),"text":str(recovered)[:1800]})
                        messages.append(self._assistant_message(content,reasoning))
                        messages.append({"role":"tool","tool_call_id":"auto_write_file","name":"write_file","content":json.dumps(recovered,ensure_ascii=False,default=str)[:12000]})
                        needs_narration=True
                        continue
                if action_required and ((not used_tool) or unresolved_failure) and correction_used<5:
                    correction_used+=1; messages.append(self._assistant_message(content,reasoning)); messages.append({"role":"user","content":"任务尚未真实完成。你必须调用实际工具完成任务：如果要创建 HTML 或其他文件，请立即调用 write_file，把完整内容写入 Desktop\\文件名，然后调用 file_info 或 read_file 验证。不要只在聊天里输出代码，也不要声称成功。"}); continue
                if action_required and used_tool and not verification_done:
                    verification_done=True
                    messages.append(self._assistant_message(content,reasoning))
                    messages.append({"role":"user","content":"现在进行最后验收检查。请根据用户原始要求和所有真实工具返回结果逐项核对：文件、界面、程序状态或电脑操作是否真的完成。不要凭感觉声称成功；如果有任何缺失或错误，立即调用合适的工具修复并继续检查。只有确认全部完成后，才用简短中文说明检查结论并给出最终答复。"})
                    self.events.emit("progress",{"kind":"verification_start","text":"正在进行最终验收检查…"})
                    continue
                final=content or response.get("reasoning")
                if not final:
                    messages.append({"role":"assistant","content":""})
                    messages.append({"role":"user","content":"上一轮没有返回可用内容。请不要结束任务，请重新检查上下文并用中文输出当前结论；如果仍有未完成的操作，请继续调用工具。"})
                    self.events.emit("progress",{"kind":"empty_response","text":"模型没有返回内容，正在重新请求…"})
                    continue
                if action_required and (not used_tool or unresolved_failure):
                    task.status=TaskStatus.FAILED; self.events.emit("task",task)
                    return "任务未确认完成：模型没有成功执行所需工具，或最近一次工具执行失败。本次没有把未完成任务伪装成成功。"
                task.status=TaskStatus.COMPLETED; self.events.emit("task",task); return final
            assistant_calls=[]
            for call in calls: assistant_calls.append({"id":call["id"],"type":"function","function":{"name":call["name"],"arguments":json.dumps(call["arguments"],ensure_ascii=False)}})
            messages.append(self._assistant_message(content,reasoning,assistant_calls))
            for call in calls:
                if task.stopped: task.status=TaskStatus.STOPPED; return "Agent 已停止。"
                name,args=call["name"],call["arguments"]; signature=json.dumps([name,args],ensure_ascii=False,sort_keys=True,default=str); duplicate[signature]+=1
                self.events.emit("progress",{"kind":"tool_start","name":name,"arguments":args,"step":step})
                if duplicate[signature]>=3:
                    blocked_signatures.add(signature)
                    result={"success":False,"error":"Repeated identical tool call blocked to prevent a loop"}
                elif "_invalid_json" in args: result={"success":False,"error":"Invalid JSON arguments","raw":args["_invalid_json"]}
                else:
                    definition=self.registry.definition(name); risk=definition.risk if definition else "low"; task.step=f"工具：{name}"; self.events.emit("task",task); self.logger.info("[ToolCall] %s %s",name,args)
                    allowed=self.permissions.decide(name,json.dumps(args,ensure_ascii=False),"完成当前 Agent 任务",risk)
                    self.logger.info("[Permission] %s %s",name,"ALLOW" if allowed else "DENY")
                    result=self.registry.execute(name,args) if allowed else {"success":False,"error":"User denied this tool call"}
                used_tool=True; unresolved_failure=not bool(result.get("success")); self.events.emit("tool",name,result); self.events.emit("progress",{"kind":"tool_result","name":name,"success":bool(result.get("success")),"text":str(result)[:1800]}); self.logger.info("[ToolResult] %s %s",name,result)
                messages.append({"role":"tool","tool_call_id":call["id"],"name":name,"content":json.dumps(result,ensure_ascii=False,default=str)[:12000]})
            needs_narration=True
        task.status=TaskStatus.FAILED; self.events.emit("task",task); return f"已达到设定的最大步骤数 {self.max_steps}，任务已停止。"
