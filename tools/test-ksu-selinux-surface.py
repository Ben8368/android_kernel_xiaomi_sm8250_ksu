#!/usr/bin/env python3
"""Check finite source-reviewed grants, not complete ROM policy correctness."""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
rules = (ROOT / 'KernelSU-Next/kernel/selinux/rules.c').read_text()
code = re.sub(r'/\*.*?\*/|//[^\n]*', '', rules, flags=re.S)
matrix = json.loads((ROOT / 'docs/validation/stage4/selinux-inventory.json').read_text())
grants = [dict(api=api, arguments=[x.strip() for x in args.split(',')][1:])
          for api, args in re.findall(r'\b(ksu_allowxperm|ksu_allow)\(([^;]*?)\);', code)]
if grants != matrix['reviewed_kernel_metadata_grants']:
    raise AssertionError('grants differ from reviewed inventory')
for grant in grants:
    if grant['api'] != 'ksu_allow' or any(not re.fullmatch(r'"[a-z_]+"', arg) for arg in grant['arguments']):
        raise AssertionError('wildcard, xperm or computed authorization reintroduced')
    if json.loads(grant['arguments'][0]) != 'kernel':
        raise AssertionError('unaudited userspace-domain grant')
if 'ksu_permissive(' in code or 'ksu_typeattribute(' in code:
    raise AssertionError('permissive or unaudited attribute exemption')
if 'if (!ksu_enforce(db, KERNEL_SU_DOMAIN))' not in code:
    raise AssertionError('must clear inherited su permissive state')
runtime = code[code.index('int handle_sepolicy('):]
if not re.search(r'\{\s*return -EOPNOTSUPP;\s*\}', runtime):
    raise AssertionError('runtime injection must remain quarantined until target policy review')
los = (ROOT / 'docs/validation/stage4/sources/sepolicy-private-su.te').read_text()
if 'permissive su;' not in los or 'userdebug_or_eng' not in los:
    raise AssertionError('inherited debug-ROM permissive finding changed')
print('PASS all', len(grants), 'bootstrap grants are finite kernel metadata/store operations; no ioctl xperms or attribute exemptions')
print('PASS inherited su permissive state explicitly cleared; root-only runtime policy mutation fails closed')
print('BLOCKED target ROM: no complete platform/vendor/product/system_ext policy or compiled sepolicy; no target compile/neverallow/PTY/Root claim')
