import json, sys, re
# Mirrors src/framework/model_spec/schema.cpp::validate_v1 for the fields we set.
CATS=None
def enum_from_cpp(fn):
    s=open('src/framework/model_spec/schema.cpp').read()
    m=re.search(r'const std::unordered_set<std::string> & '+fn+r'\(\).*?\{(.*?)\}\s*;', s, re.S)
    return set(re.findall(r'"([^"]+)"', m.group(1)))
kinds=enum_from_cpp('dependency_kinds'); scopes=enum_from_cpp('dependency_scopes')
cats=enum_from_cpp('categories'); stats=enum_from_cpp('statuses')
tasks=enum_from_cpp('tasks'); modes=enum_from_cpp('modes')
fmts=enum_from_cpp('source_formats'); precs=enum_from_cpp('precisions')
otypes=enum_from_cpp('option_types')
errs=[]
def req(o,k,path):
    if k not in o: errs.append(f"{path}: missing required field '{k}'"); return None
    return o[k]
d=json.load(open(sys.argv[1])); P='spec'
for k in ("family","display_name","category","status","tasks","modes","languages",
          "runtime","capabilities","options","packages","dependencies","ui","sources"):
    req(d,k,P)
fam=d.get('family')
if d.get('category') not in cats: errs.append(f"category '{d.get('category')}' not in {sorted(cats)}")
if d.get('status') not in stats: errs.append(f"status '{d.get('status')}' not in {sorted(stats)}")
for t in d.get('tasks',[]):
    if t not in tasks: errs.append(f"task '{t}' not in {sorted(tasks)}")
for m in d.get('modes',[]):
    if m not in modes: errs.append(f"mode '{m}' not in {sorted(modes)}")
# options: all three scopes are mandatory even when empty
opts = d.get('options') or {}
for scope in ("request","session","load"):
    if scope not in opts:
        errs.append(f"{P}.options: missing required field '{scope}'")
declared={}
for scope,items in opts.items():
    declared[scope]=set()
    for i,o in enumerate(items):
        pp=f"{P}.options.{scope}[{i}]"
        # schema.cpp::validate_option requires name, type and required.
        # description is NOT required; this had it backwards, so specs that the
        # C++ rejects at load time were passing here.
        n=req(o,'name',pp); req(o,'type',pp); req(o,'required',pp)
        if 'required' in o and not isinstance(o['required'], bool):
            errs.append(f"{pp}.required: expected bool")
        if o.get('type') not in otypes: errs.append(f"{pp}.type '{o.get('type')}' not in {sorted(otypes)}")
        if n: declared[scope].add(n)
# packages
pkg_ids=set(); has_def=('package_defaults' in d and 'download' in d.get('package_defaults',{}))
for i,pk in enumerate(d.get('packages',[])):
    pp=f"{P}.packages[{i}]"
    for k in ("id","display_name","format","precision","target_directory","files"): req(pk,k,pp)
    if pk.get('format') not in fmts: errs.append(f"{pp}.format '{pk.get('format')}' not in {sorted(fmts)}")
    if pk.get('precision') not in precs: errs.append(f"{pp}.precision '{pk.get('precision')}' not in {sorted(precs)}")
    if not pk.get('files'): errs.append(f"{pp}.files must not be empty")
    if 'download' not in pk and not has_def: errs.append(f"{pp}.download missing and no package_defaults.download")
    pkg_ids.add(pk.get('id'))
# dependencies
for i,dep in enumerate(d.get('dependencies',[])):
    pp=f"{P}.dependencies[{i}]"
    k=req(dep,'kind',pp); req(dep,'family',pp); sc=req(dep,'scope',pp)
    op=req(dep,'option',pp); rq=req(dep,'required',pp)
    if k and k not in kinds: errs.append(f"{pp}.kind '{k}' not in {sorted(kinds)}")
    if sc and sc not in scopes: errs.append(f"{pp}.scope '{sc}' not in {sorted(scopes)}")
    if 'package' in dep: errs.append(f"{pp}.package: dependency package hints are not part of the core contract")
    if 'required_for' in dep: errs.append(f"{pp}.required_for: use typed required_when")
    if op and (sc not in declared or op not in declared.get(sc,set())):
        errs.append(f"{pp}.option '{op}' is not declared in options.{sc}")
    if rq is False and 'required_when' not in dep: errs.append(f"{pp}.required_when: optional dependencies require typed conditions")
# ui
ui=d.get('ui') or {}
rec=req(ui,'recommended_package',f"{P}.ui")
if rec and rec not in pkg_ids: errs.append(f"{P}.ui.recommended_package unknown package '{rec}'")
# sources
for i,s in enumerate(d.get('sources',[])):
    pp=f"{P}.sources[{i}]"
    f_=req(s,'format',pp); roots=req(s,'roots',pp) or {}
    if f_ and f_ not in fmts: errs.append(f"{pp}.format '{f_}' not in {sorted(fmts)}")
    for mapname in ("files","optional_files","tensors","optional_tensors"):
        for rid,ref in (s.get(mapname) or {}).items():
            src = ref if isinstance(ref,str) else ref.get('source')
            if not src or ':' not in src or src.index(':')==0:
                errs.append(f"{pp}.{mapname}.{rid}: invalid resource reference '{src}'"); continue
            root=src.split(':')[0]
            if root not in roots: errs.append(f"{pp}.{mapname}.{rid}: unknown root '{root}'")
print("\n".join(f"  FAIL {e}" for e in errs) if errs else "  spec passes every rule mirrored from schema.cpp")
sys.exit(1 if errs else 0)
