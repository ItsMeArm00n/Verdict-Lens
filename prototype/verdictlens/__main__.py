"""Run with python -m verdictlens; no input argument runs the bundled examples."""
import argparse
import json
from pathlib import Path
from . import Auditor

def main():
    parser = argparse.ArgumentParser(description='Run a fully local VerdictLens audit.')
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[1] / 'examples/sample_applicants.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding='utf-8-sig'))
        auditor = Auditor()
        result = [auditor.run(a) for a in data] if isinstance(data, list) else auditor.run(data)
        content = json.dumps(result, indent=2, allow_nan=False) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding='utf-8')
            print(f'Saved results to {args.output}')
        else:
            print(content, end='')
    except (ValueError, OSError) as error:
        parser.exit(2, f'VerdictLens: {error}\n')

if __name__ == '__main__':
    main()
