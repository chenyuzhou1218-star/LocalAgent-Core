from __future__ import annotations
import ast, json, os, subprocess, sys
from pathlib import Path
from collections import Counter

SKIP={'.git','.venv','venv','node_modules','__pycache__','dist','build','.idea'}

def _root(path):
    p=Path(path or '.').expanduser().resolve()
    if not p.exists(): raise FileNotFoundError(str(p))
    return p

def scan_project(path='.', max_files=1500):
    root=_root(path); files=[]; counts=Counter(); manifests=[]; python_symbols=[]
    for p in root.rglob('*'):
        if any(part in SKIP for part in p.parts): continue
        if not p.is_file(): continue
        rel=str(p.relative_to(root)); files.append(rel); counts[p.suffix.lower() or '[no extension]']+=1
        if p.name.lower() in {'readme.md','readme.txt','pyproject.toml','package.json','requirements.txt','go.mod','cargo.toml'}: manifests.append(rel)
        if p.suffix.lower()=='.py' and len(python_symbols)<200:
            try:
                tree=ast.parse(p.read_text(encoding='utf-8',errors='replace'))
                for node in ast.walk(tree):
                    if isinstance(node,(ast.FunctionDef,ast.ClassDef)): python_symbols.append({'file':rel,'kind':type(node).__name__,'name':node.name,'line':node.lineno})
            except SyntaxError as exc: python_symbols.append({'file':rel,'kind':'syntax_error','line':exc.lineno,'error':exc.msg})
        if len(files)>=int(max_files): break
    files.sort()
    return {'success':True,'root':str(root),'file_count':len(files),'truncated':len(files)>=int(max_files),'extensions':dict(counts),'manifests':manifests,'python_symbols':python_symbols,'files':files[:500]}

def review_project(path='.'):
    root=_root(path); findings=[]; checked=0
    for p in root.rglob('*.py'):
        if any(part in SKIP for part in p.parts): continue
        checked+=1
        try: ast.parse(p.read_text(encoding='utf-8',errors='replace'))
        except SyntaxError as exc: findings.append({'severity':'error','file':str(p.relative_to(root)),'line':exc.lineno or 0,'message':exc.msg})
    git=[]
    try:
        proc=subprocess.run(['git','-C',str(root),'diff','--check'],capture_output=True,text=True,encoding='utf-8',errors='replace')
        if proc.stdout.strip() or proc.stderr.strip(): git=(proc.stdout+proc.stderr).strip().splitlines()[:80]
    except Exception: pass
    for p in root.rglob('*'):
        if p.is_file() and not any(part in SKIP for part in p.parts):
            try:
                text=p.read_text(encoding='utf-8',errors='ignore')
                for i,line in enumerate(text.splitlines(),1):
                    if 'TODO' in line or 'FIXME' in line: findings.append({'severity':'warning','file':str(p.relative_to(root)),'line':i,'message':line.strip()[:240]})
            except Exception: pass
    return {'success':not any(x['severity']=='error' for x in findings),'root':str(root),'python_files_checked':checked,'findings':findings[:200],'git_diff_check':git}

def run_project_tests(path='.'):
    root=_root(path); commands=[]
    if (root/'tests').exists() or list(root.rglob('test_*.py')):
        commands.append([sys.executable,'-m','pytest','-q'])
    commands.append([sys.executable,'-m','compileall','-q','.'])
    results=[]
    for command in commands:
        try:
            p=subprocess.run(command,cwd=str(root),capture_output=True,text=True,encoding='utf-8',errors='replace')
            results.append({'command':' '.join(command),'exit_code':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:]})
            if p.returncode!=0: break
        except Exception as exc: results.append({'command':' '.join(command),'exit_code':-1,'error':str(exc)}); break
    return {'success':all(item.get('exit_code')==0 for item in results),'root':str(root),'results':results}

def git_status(path='.'):
    root=_root(path)
    try:
        p=subprocess.run(['git','-C',str(root),'status','--short'],capture_output=True,text=True,encoding='utf-8',errors='replace')
        return {'success':p.returncode==0,'root':str(root),'status':p.stdout,'stderr':p.stderr}
    except Exception as exc: return {'success':False,'error':str(exc)}
