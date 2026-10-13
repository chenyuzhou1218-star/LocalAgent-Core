from __future__ import annotations
import json, os
from pathlib import Path

def _dirs():
    root=Path(__file__).resolve().parents[1]
    return [root/'extensions',root/'.codex'/'skills',Path.home()/'.codex'/'skills']

def list_extensions():
    items=[]
    for base in _dirs():
        if not base.exists(): continue
        for p in base.iterdir():
            if p.is_dir():
                skill=p/'SKILL.md'; manifest=p/'manifest.json'
                items.append({'name':p.name,'path':str(p),'type':'skill' if skill.exists() else 'extension','has_manifest':manifest.exists(),'has_skill':skill.exists()})
    return {'success':True,'items':items,'count':len(items)}

def read_extension(name):
    for base in _dirs():
        p=base/name
        if p.exists() and p.is_dir():
            result={'success':True,'name':name,'path':str(p)}
            skill=p/'SKILL.md'; manifest=p/'manifest.json'
            if skill.exists(): result['skill']=skill.read_text(encoding='utf-8',errors='replace')[:12000]
            if manifest.exists():
                try: result['manifest']=json.loads(manifest.read_text(encoding='utf-8'))
                except Exception: result['manifest_error']='invalid JSON'
            return result
    return {'success':False,'error':f'Extension not found: {name}'}
