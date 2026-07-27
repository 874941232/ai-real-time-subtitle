import os
import sys
import json
import requests
from pathlib import Path

# Download to project root (same folder as the exe) so it's easy to share
target = Path(__file__).resolve().parent / 'SenseVoice-Small-ONNX'
target.mkdir(parents=True, exist_ok=True)
print(f'Target: {target}')

# Official model repo on ModelScope
REPO = 'iic/SenseVoiceSmall-onnx'
base_url = f'https://www.modelscope.cn/api/v1/models/{REPO}/repo'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def download_file(repo_file: str, save_as: str = None) -> bool:
    """Download a single file from ModelScope API."""
    save_name = save_as or repo_file
    out = target / save_name
    if out.exists():
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f'{save_name} already exists ({size_mb:.1f}MB)')
        return True

    url = f'{base_url}?Revision=master&FilePath={repo_file}'
    print(f'Downloading {repo_file} -> {save_name} ...')
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=300)
        if r.status_code == 200:
            total = int(r.headers.get('Content-Length', 0))
            downloaded = 0
            with open(out, 'wb') as fw:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    fw.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        print(f'  {percent:.1f}%', end='\r')
            size_mb = out.stat().st_size / (1024 * 1024)
            print(f'\n{save_name} done ({size_mb:.1f}MB)')
            return True
        else:
            print(f'  HTTP {r.status_code}: {r.text[:200]}')
            return False
    except Exception as e:
        print(f'  Error: {e}')
        return False


def convert_tokens_json_to_txt():
    """Convert official tokens.json to tokens.txt for engine compatibility."""
    json_path = target / 'tokens.json'
    txt_path = target / 'tokens.txt'
    if txt_path.exists():
        return True
    if not json_path.exists():
        return False
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # tokens.json is usually a dict mapping id -> token, or a list
        tokens = []
        if isinstance(data, dict):
            # Sort by key (id) and extract values
            for k in sorted(data.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                tokens.append(str(data[k]))
        elif isinstance(data, list):
            tokens = [str(t) for t in data]
        with open(txt_path, 'w', encoding='utf-8') as f:
            for t in tokens:
                f.write(t + '\n')
        print(f'Converted tokens.json -> tokens.txt ({len(tokens)} tokens)')
        return True
    except Exception as e:
        print(f'Failed to convert tokens.json: {e}')
        return False


def convert_config_yaml_to_json():
    """Extract language map from config.yaml to config.json."""
    yaml_path = target / 'config.yaml'
    json_path = target / 'config.json'
    if json_path.exists():
        return True
    if not yaml_path.exists():
        return False
    try:
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        # Extract language token mapping if present
        lang_map = {}
        if isinstance(cfg, dict):
            # Try common paths for language config
            if 'model_conf' in cfg and isinstance(cfg['model_conf'], dict):
                mc = cfg['model_conf']
                if 'language' in mc:
                    lang_map = mc['language']
            # Fallback: write entire config
            out = {"language": lang_map}
            # Add common SenseVoice language tokens as fallback
            if not lang_map:
                out["language"] = {
                    "zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4
                }
        else:
            out = {"language": {"zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4}}
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'Converted config.yaml -> config.json')
        return True
    except ImportError:
        # No yaml library, create minimal config
        out = {"language": {"zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4}}
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'Created config.json (yaml not installed)')
        return True
    except Exception as e:
        print(f'Failed to convert config.yaml: {e}')
        return False


def try_modelscope_sdk() -> bool:
    """Fallback: use modelscope snapshot_download."""
    try:
        from modelscope.hub.snapshot_download import snapshot_download
        print('[SDK] Trying modelscope snapshot_download...')
        sdk_dir = snapshot_download(REPO, cache_dir=str(target.parent.parent))
        # Copy files from SDK cache to our target dir with correct names
        sdk_path = Path(sdk_dir)
        mappings = {
            'model_quant.onnx': 'model.onnx',
            'tokens.json': 'tokens.json',
            'config.yaml': 'config.yaml',
        }
        for src_name, dst_name in mappings.items():
            src = sdk_path / src_name
            if src.exists():
                dst = target / dst_name
                if not dst.exists():
                    import shutil
                    shutil.copy2(str(src), str(dst))
                    print(f'  Copied {src_name} -> {dst_name}')
        return True
    except Exception as e:
        print(f'[SDK] Failed: {e}')
        return False


# Download from official repo (quantized, 241MB)
files_to_download = [
    ('model_quant.onnx', 'model.onnx'),   # rename to match engine expectation
    ('tokens.json', 'tokens.json'),
    ('config.yaml', 'config.yaml'),
]

all_ok = True
for repo_file, save_name in files_to_download:
    if not download_file(repo_file, save_name):
        all_ok = False

# Fallback to SDK if direct download failed
if not all_ok:
    print('\nDirect download failed, trying modelscope SDK...')
    if try_modelscope_sdk():
        all_ok = True
        print('SDK download succeeded.')
    else:
        print('SDK download also failed.')
        print('\nPlease try manual download:')
        print(f'  1. Visit https://www.modelscope.cn/models/{REPO}/files')
        print('  2. Download model_quant.onnx, tokens.json, config.yaml')
        print(f'  3. Place them in: {target}')
        print('  4. Rename model_quant.onnx -> model.onnx')
        sys.exit(1)

# Convert file formats for engine compatibility
convert_tokens_json_to_txt()
convert_config_yaml_to_json()

print('\nVerification:')
required = ['model.onnx', 'config.json', 'tokens.txt']
for f in required:
    p = target / f
    if p.exists():
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f'  OK {f}: {size_mb:.1f}MB')
    else:
        print(f'  MISSING {f}')
