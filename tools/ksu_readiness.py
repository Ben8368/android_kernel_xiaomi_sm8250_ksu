"""Evidence checks for the seven independent KernelSU readiness claims.

Checksums bind inspectable local results to inputs; they are not signatures from
an independent auditor. Runtime/security claims cannot be promoted by editing a
status JSON. Supporting those claims requires an explicit reviewed validator.
"""
import hashlib
import json
import pathlib
import re
import subprocess

from ksu_audit import ROOT, digest, prove_sources

REQUIRED_TESTS = {
    'stage3-suite', 'allowlist-concurrency', 'seccomp-policy',
    'selinux-surface', 'readiness-negative',
    'protected-native-tree', 'build-evidence-negative',
}
GATE_NAMES = ('compile', 'offline_compatibility', 'static_security',
              'target_rom_sepolicy', 'boot_inputs', 'device_boot', 'device_root')
BUILD_TOOLS = ('tools/build-umi.sh', 'tools/package-umi-dt.py',
               'tools/prepare-ksu.py', 'tools/prepare-ksu.sh', 'tools/ksu_audit.py',
               'tools/record-umi-provenance.py', 'tools/umi-toolchain.lock.json',
               'tools/third_party/mkdtboimg.py', 'tools/third_party/mkdtboimg.source.json')


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def native_path(path):
    return (not path.startswith(('docs/', 'tools/', 'compat/')) and
            path not in ('KernelSU-Next', 'README.md', '.gitattributes', '.gitignore', '.gitmodules')) or path in BUILD_TOOLS


def native_tree(ref):
    data = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-rz', ref])
    entries = []
    for record in data.split(b'\0'):
        if not record:
            continue
        metadata, path = record.split(b'\t', 1)
        if native_path(path.decode()):
            entries.append(metadata + b'\t' + path)
    return hashlib.sha256(b'\0'.join(entries)).hexdigest()


def current_inputs():
    proof = prove_sources(False)
    dirty = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', 'HEAD'], text=True).splitlines()
    dirty += subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    require(not any(native_path(p) for p in dirty), 'uncommitted native/build inputs')
    code = {}
    for p in sorted((ROOT / 'tools').rglob('*')):
        if p.is_file() and p.suffix in ('.py', '.sh', '.json') and '__pycache__' not in p.parts:
            code[str(p.relative_to(ROOT))] = digest(p)
    for stage in ('stage2', 'stage3', 'stage4'):
        d = ROOT / 'docs/validation' / stage
        for p in sorted((d / 'sources').rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                code[str(p.relative_to(ROOT))] = digest(p)
        for name in ('sources.lock.json', 'selinux-inventory.json', 'reviewed-kernel-metadata.te'):
            if (d / name).exists():
                code[str((d / name).relative_to(ROOT))] = digest(d / name)
    return dict(native_tree_sha256=native_tree('HEAD'),
                patch_queue_sha256=proof['patch_queue_sha256'],
                effective_ksu_kernel_sha256=proof['effective_ksu_kernel_sha256'],
                offline_code_sha256=code)


def evidence_file(directory, name):
    require(isinstance(name, str), 'invalid evidence filename')
    directory = directory.resolve()
    p = (directory / name).resolve()
    require(p.is_relative_to(directory), 'evidence path escapes its directory')
    require(p.is_file(), 'missing evidence: ' + name)
    return p


def json_file(directory, name):
    return json.loads(evidence_file(directory, name).read_text())


def verify_files(directory, records):
    require(isinstance(records, dict) and records, 'missing evidence hashes')
    for name, sha in records.items():
        require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'invalid evidence hash')
        require(digest(evidence_file(directory, name)) == sha, 'changed evidence: ' + name)


def verify_compile(directory, inputs, build_dir=None):
    record = json_file(directory, 'build-result.json')
    verify_files(directory, record['files'])
    expected = {'build-console.log', 'build.exit', 'provenance.json', 'source-before.json',
                'linked-verification.json', 'build.config', 'modules.sha256.json', 'build-contract.json'}
    require(expected <= record['files'].keys(), 'incomplete build evidence')
    require(evidence_file(directory, 'build.exit').read_text().strip() == '0', 'build did not exit zero')
    log = evidence_file(directory, 'build-console.log').read_text()
    require(re.search(r'^SUCCESS ', log, re.M), 'missing completed build marker')
    require(re.search(r'^COMMAND:.* Image modules dtbs$', log, re.M), 'missing full build command')
    p = json_file(directory, 'provenance.json')
    linked = json_file(directory, 'linked-verification.json')
    require(json_file(directory, 'source-before.json') == p['source'], 'pre/post build sources differ')
    require(p['source']['patch_queue_sha256'] == inputs['patch_queue_sha256'], 'built patch queue is stale')
    require(p['source']['effective_ksu_kernel_sha256'] == inputs['effective_ksu_kernel_sha256'], 'built KernelSU source is stale')
    require(native_tree(p['source']['custom_branch_sha']) == inputs['native_tree_sha256'], 'built native/config/tool inputs differ')
    require(p['source']['unexplained_dirty'] is False, 'unexplained build dirtiness')
    require(linked['build_invocation_head'] == p['source']['custom_branch_sha'], 'build commit identity mismatch')
    require('r596125' in p['clang'] and '22.0.2' in p['clang'], 'wrong Clang version')
    require(p['toolchain_lock_sha256'] == digest(ROOT / 'tools/umi-toolchain.lock.json'), 'wrong toolchain lock')
    require(p['config_sha256'] == digest(evidence_file(directory, 'build.config')), 'config hash mismatch')
    cfg = evidence_file(directory, 'build.config').read_text()
    for symbol in ('LTO', 'LTO_CLANG', 'THINLTO', 'CFI', 'CFI_CLANG', 'SECCOMP', 'SECCOMP_FILTER', 'SECURITY_SELINUX', 'KSU'):
        require(f'CONFIG_{symbol}=y\n' in cfg, 'missing required config: ' + symbol)
    for symbol in ('CFI_PERMISSIVE', 'SECURITY_SELINUX_DISABLE', 'KSU_DEBUG'):
        require(f'# CONFIG_{symbol} is not set\n' in cfg, 'unsafe config: ' + symbol)
    require(linked['cfi_flags_verified'] and linked['unresolved_strong_symbols'] == 0, 'link/CFI failure')
    require(linked['image_sha256'] == p['image_sha256'] if 'image_sha256' in linked else
            any(x['path'] == 'arch/arm64/boot/Image' and x['sha256'] == p['image_sha256'] for x in linked['artifacts']), 'Image identity mismatch')
    require(linked['vmlinux_sha256'] == p['vmlinux_sha256'], 'vmlinux identity mismatch')
    require(linked['dtb_count'] > 0 and linked['dtbo_count'] > 0 and linked['module_count'] > 0, 'incomplete modules/DT build')
    modules = json_file(directory, 'modules.sha256.json')
    require(isinstance(modules, dict) and all(
        name.endswith('.ko') and not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts and
        isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha) for name, sha in modules.items()), 'invalid module inventory')
    require(len(modules) == linked['module_count'], 'module inventory mismatch')
    contract = json_file(directory, 'build-contract.json')
    require(contract['status'] == 'PASS' and contract['built_source_commit'] == p['source']['custom_branch_sha'], 'compiled Manager/CFI contract mismatch')
    require(contract['compiled_cfi'] is True and contract['linked_ksu_paths_present'] is True, 'compiled CFI/entry contract failure')
    lock = json.loads((ROOT / 'tools/ksu-userland.lock.json').read_text())
    require(contract['compiled_certificate_sha256'] == lock['certificate_sha256'], 'compiled Manager trust anchor mismatch')
    if build_dir is not None:
        build_dir = pathlib.Path(build_dir)
        for name, sha in {'vmlinux': p['vmlinux_sha256'], **modules,
                          **{x['path']: x['sha256'] for x in linked['artifacts']}}.items():
            require(digest(evidence_file(build_dir, name)) == sha, 'artifact rehash failed: ' + name)
    return dict(status='PASS', evidence=sorted(record['files']), built_source_commit=p['source']['custom_branch_sha'],
                image_sha256=p['image_sha256'], artifact_rehash=build_dir is not None,
                scope='Image/modules/dtbs compile/link; archived evidence' if build_dir is None else 'compile/link evidence and current artifact bytes rehashed')


def verify_offline(directory, inputs):
    record = json_file(directory, 'offline-results.json')
    require(record['inputs'] == inputs, 'offline results do not match current code/source inputs')
    tests = record['tests']
    require(len({x['id'] for x in tests}) == len(tests), 'duplicate test IDs')
    require(REQUIRED_TESTS <= {x['id'] for x in tests}, 'required offline tests missing')
    for test in tests:
        require(test['exit_code'] == 0, 'offline test failed: ' + test['id'])
        verify_files(directory, {test['log']: test['sha256']})
        require(evidence_file(directory, test['log']).stat().st_size > 0, 'empty test log')
    return dict(status='PASS', evidence=[x['log'] for x in tests], source_commit=record['source_commit'],
                scope='host adapters, fixtures, source regressions and release cryptography; NOT Android execution')


def blocked(detail, evidence=()):
    return dict(status='BLOCKED', detail=detail, evidence=list(evidence))


def assess(directory, build_dir=None):
    directory = pathlib.Path(directory)
    try:
        inputs = current_inputs()
        source_error = None
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        inputs, source_error = None, str(e)
    gates = {}
    for name, validator in [('compile', verify_compile), ('offline_compatibility', verify_offline)]:
        try:
            require(inputs is not None, source_error)
            gates[name] = validator(directory, inputs, build_dir) if name == 'compile' else validator(directory, inputs)
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as e:
            gates[name] = blocked(str(e))
    # No unverified PASS bool, empty report, host mock or successful compile can
    # certify these claims. Each needs its own reviewed evidence validator.
    gates['static_security'] = blocked(
        'UID/package/certificate lifecycle and durable revocation remain unresolved; exec kprobe credential allocation/SELinux credential mutation require context audit. No validated ordinary-app Root architecture.',
        ['docs/ROOT-SECURITY.md', 'docs/SECCOMP-FEASIBILITY.md'])
    gates['static_security']['regression_tests'] = gates['offline_compatibility']['status']
    gates['target_rom_sepolicy'] = blocked(
        'No exact full platform/vendor/product/system_ext policy or compiled policy; target compilation, neverallow and effective-domain checks not run.',
        ['docs/SELINUX-MATRIX.md', 'docs/validation/stage4/selinux-inventory.json', 'docs/validation/stage4/sources.lock.json'])
    gates['boot_inputs'] = blocked(
        'No precisely matching umi ROM target-files/Boot/ramdisk/DTBO/vbmeta/recovery and verified rollback bundle.',
        ['docs/BOOT-FORMAT.md'])
    gates['device_boot'] = blocked('No device boot/hardware/log evidence for this Image and ROM.', ['docs/DEVICE-TEST-PLAN.md'])
    gates['device_root'] = blocked(
        'Official ordinary-app su is incompatible with retained App Seccomp; no authorized/unauthorized/revoked Android Root tests. Manager detection or bootstrap is insufficient.',
        ['docs/SECCOMP-FEASIBILITY.md', 'docs/DEVICE-TEST-PLAN.md'])
    for gate in gates.values():
        gate['materials'] = {name: digest(ROOT / name) for name in gate['evidence'] if (ROOT / name).is_file()}
    require(set(gates) == set(GATE_NAMES), 'readiness category mismatch')
    return dict(status='BLOCKED', conclusion='NO-GO', manual_device_test_ready=False, gates=gates,
                evidence_directory=str(directory.resolve()),
                scope='current v1.1.1 direct su architecture under unchanged app Seccomp; no runtime success is inferred')
