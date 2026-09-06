"""Synthetic contract regression tests, never native generation or visual approval."""
from pathlib import Path
import argparse
import copy
import json
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import scientific_illustration as si
import validate_figure_intent as vi


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def ref(path):
    return {'file': str(path), 'sha256': si.sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=None, metavar='NEW_REPORT_DIR',
                        help='New directory for the report and all synthetic fixtures; defaults to a new system temporary directory.')
    args = parser.parse_args()
    if args.output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix='scientific-illustration-tests-')).resolve()
    else:
        output_dir = args.output_dir.resolve()
        try:
            output_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            parser.error('--output-dir must be a new directory; existing artifacts are never overwritten')
    from PIL import Image
    run = output_dir / 'fixtures'
    run.mkdir()
    source = write(run / 'model.json', {'test_fixture': True, 'approved_model': 'original'})
    brief = {'figure_id': 'test-native', 'backend_preference': 'imagegen', 'purpose': '测试模型说明图示',
             'caption_zh': '测试机制', 'nodes': [{'id': 'a', 'label_zh': '输入'}], 'edges': [],
             'narrative_role': 'mechanism', 'style': {'palette': ['#0088FF'], 'composition': '从左到右'},
             'source_files': [ref(source)]}
    brief_path = write(run / 'brief.json', brief)
    tools = write(run / 'tools.json', {'names': ['image_gen__imagegen']})
    si.prepare(brief_path, tools, run / 'prepared')
    request_path = run / 'prepared/request.json'
    prompt_path = run / 'prepared/prompt.txt'
    png = run / 'TEST_FIXTURE_NOT_NATIVE.png'
    Image.new('RGB', (512, 512), 'white').save(png)
    record = {'test_fixture': True, 'tool_name': 'image_gen__imagegen',
              'request_sha256': si.sha(request_path), 'output_sha256': si.sha(png),
              'response': {'test_fixture': True, 'status': 'completed', 'output': str(png)}}
    record_path = write(run / 'TEST_FIXTURE_TOOL_RECORD.json', record)
    receipt = {'test_fixture': True, 'actual_backend': 'imagegen', 'tool_name': 'image_gen__imagegen',
               'status': 'completed', 'native_generation': True, 'output_sha256': si.sha(png),
               'request': ref(request_path), 'prompt': ref(prompt_path), 'tool_record': ref(record_path)}
    receipt_path = write(run / 'TEST_FIXTURE_RECEIPT.json', receipt)
    finalized = run / 'finalized'
    report = si.finalize(brief_path, png, receipt_path, finalized)
    results = {'test_kind': 'synthetic-contract-regression', 'actual_native_generation': False,
               'visual_review_performed': False, 'fixture_directory': str(run), 'tests': []}
    entry = {'figure_id': brief['figure_id'], 'narrative_role': 'mechanism', 'backend_preference': 'imagegen',
             'editable_output': str(finalized / 'brief.json'), 'latex_output': str(finalized / 'figure.png'),
             'backend_report': str(finalized / 'backend_report.json'),
             'backend_report_sha256': si.sha(finalized / 'backend_report.json'),
             'visual_grammar': {'style_profile': 'cumcm-vivid'}, 'source_data': brief['source_files']}

    def validate(e=entry):
        return vi.validate_backend_report(e, 'fixture', run,
            si.sha(Path(e['editable_output'])), si.sha(Path(e['latex_output'])))

    errors = validate()
    results['tests'].append({'name': 'synthetic_valid_chain', 'passed': not errors, 'errors': errors})
    if errors:
        results['passed'] = False
        write(output_dir / 'regression-results.json', results)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    def rejected_finalize(name, mutate):
        fresh_brief, fresh_receipt, fresh_record = copy.deepcopy(brief), copy.deepcopy(receipt), copy.deepcopy(record)
        mutate(fresh_brief, fresh_receipt, fresh_record)
        write(brief_path, fresh_brief)
        write(record_path, fresh_record)
        fresh_receipt['tool_record'] = ref(record_path)
        write(receipt_path, fresh_receipt)
        try:
            si.finalize(brief_path, png, receipt_path, run / name)
            err = None
        except (ValueError, KeyError, TypeError) as exc:
            err = str(exc)
        results['tests'].append({'name': name, 'passed': err is not None, 'error': err})
        write(brief_path, brief)
        write(record_path, record)
        write(receipt_path, receipt)

    rejected_finalize('reject_changed_brief', lambda b, r, t: b['nodes'][0].update(label_zh='全新机制'))
    rejected_finalize('reject_failed_tool_record', lambda b, r, t: t.update(response={'status': 'failed', 'isError': True}))
    rejected_finalize('reject_unrelated_primary_tool', lambda b, r, t: r.update(tool_name='unrelated_tool', companion_tools=['image_gen__imagegen']))

    final_report_path = finalized / 'backend_report.json'
    original_report = si.load(final_report_path)
    final_receipt_path = finalized / 'receipt.json'
    original_receipt = si.load(final_receipt_path)
    final_record_path = finalized / 'tool_record.json'
    original_record = si.load(final_record_path)
    final_brief_path = finalized / 'brief.json'
    original_brief = si.load(final_brief_path)

    def final_mutation(name, mutate):
        rp, rc, tr, bf = map(copy.deepcopy, (original_report, original_receipt, original_record, original_brief))
        mutate(rp, rc, tr, bf)
        write(final_brief_path, bf)
        write(final_record_path, tr)
        rc['tool_record'] = ref(final_record_path)
        write(final_receipt_path, rc)
        rp['receipt'] = ref(final_receipt_path)
        for output in rp['outputs']:
            if output['path'] == 'brief.json':
                output['sha256'] = si.sha(final_brief_path)
        write(final_report_path, rp)
        changed_entry = copy.deepcopy(entry)
        changed_entry['backend_report_sha256'] = si.sha(final_report_path)
        errs = validate(changed_entry)
        results['tests'].append({'name': name, 'passed': bool(errs), 'errors': errs})
        write(final_brief_path, original_brief)
        write(final_record_path, original_record)
        write(final_receipt_path, original_receipt)
        write(final_report_path, original_report)

    final_mutation('reject_final_record_failed_uppercase', lambda rp, rc, tr, bf: tr.update(response={'status': 'FAILED'}))
    final_mutation('reject_final_record_nested_failure', lambda rp, rc, tr, bf: tr.update(response={'structuredContent': {'status': 'failed'}}))
    final_mutation('reject_final_record_request_mismatch', lambda rp, rc, tr, bf: tr.update(request_sha256='0'*64))
    final_mutation('reject_final_record_output_mismatch', lambda rp, rc, tr, bf: tr.update(output_sha256='0'*64))
    final_mutation('reject_final_primary_tool_masking', lambda rp, rc, tr, bf: rc.update(tool_name='unrelated_tool', companion_tools=['image_gen__imagegen']))
    final_mutation('reject_refreshed_editable_brief', lambda rp, rc, tr, bf: bf['nodes'][0].update(label_zh='改变后的机制'))
    final_mutation('reject_generation_brief_hash', lambda rp, rc, tr, bf: rp.update(generation_brief_sha256='0'*64))
    final_mutation('reject_incorrect_pixel_dimensions', lambda rp, rc, tr, bf: rp.update(pixel_size=[999, 999]))
    for backend_name, names in (
        ('image2_sync', ['mcp__codex_image2__generate']),
        ('image2_async', ['mcp__codex_image2__generate_start', 'mcp__codex_image2__generate_status']),
    ):
        branch = run / backend_name
        branch.mkdir()
        bridge_brief = copy.deepcopy(brief)
        bridge_brief['backend_preference'] = 'image2'
        bridge_brief_path = write(branch / 'brief.json', bridge_brief)
        bridge_tools_path = write(branch / 'tools.json', {'names': names})
        si.prepare(bridge_brief_path, bridge_tools_path, branch / 'prepared')
        bridge_request = branch / 'prepared/request.json'
        bridge_record = copy.deepcopy(record)
        bridge_record.update(tool_name=names[0], request_sha256=si.sha(bridge_request))
        bridge_record_path = write(branch / 'TEST_FIXTURE_TOOL_RECORD.json', bridge_record)
        bridge_receipt = copy.deepcopy(receipt)
        bridge_receipt.update(actual_backend='image2', tool_name=names[0], request=ref(bridge_request),
            prompt=ref(branch / 'prepared/prompt.txt'), tool_record=ref(bridge_record_path))
        bridge_receipt_path = write(branch / 'TEST_FIXTURE_RECEIPT.json', bridge_receipt)
        try:
            si.finalize(bridge_brief_path, png, bridge_receipt_path, branch / 'finalized')
            bridge_entry = copy.deepcopy(entry)
            bridge_entry.update(backend_preference='image2', editable_output=str(branch / 'finalized/brief.json'),
                latex_output=str(branch / 'finalized/figure.png'),
                backend_report=str(branch / 'finalized/backend_report.json'),
                backend_report_sha256=si.sha(branch / 'finalized/backend_report.json'))
            bridge_errors = validate(bridge_entry)
        except (ValueError, TypeError, KeyError) as exc:
            bridge_errors = [str(exc)]
        results['tests'].append({'name': f'synthetic_valid_{backend_name}_chain',
                                'passed': not bridge_errors, 'errors': bridge_errors})
    results['passed'] = all(test['passed'] for test in results['tests'])
    results['candidate_hashes'] = {name: si.sha(SCRIPTS / name) for name in (
        'scientific_illustration.py', 'validate_figure_intent.py', 'visual_review_contract.py')}
    results['report_file'] = str(output_dir / 'regression-results.json')
    write(output_dir / 'regression-results.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
