#!/usr/bin/env python3
"""
依赖包分析工具
分析项目中实际使用的依赖包，生成精简的requirements.txt
"""

import ast
import sys
from pathlib import Path
from typing import Set, Dict
import subprocess

def extract_imports_from_file(file_path: str) -> Set[str]:
    """从Python文件中提取import语句"""
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    
    except Exception as e:
        print(f"警告: 无法解析文件 {file_path}: {e}")
    
    return imports

def get_project_imports(project_dir: str = '.') -> Set[str]:
    """获取项目中所有Python文件的import"""
    all_imports = set()
    
    for py_file in Path(project_dir).glob('*.py'):
        if py_file.name.startswith('__') or py_file.name == 'generate_requirements.py':
            continue
        
        file_imports = extract_imports_from_file(str(py_file))
        all_imports.update(file_imports)
        print(f"📄 {py_file.name}: {sorted(file_imports)}")
    
    return all_imports

def filter_third_party_packages(imports: Set[str]) -> Set[str]:
    """过滤出第三方包"""
    
    # Python标准库模块
    stdlib_modules = {
        'asyncio', 'json', 're', 'datetime', 'logging', 'sys', 'os', 
        'pathlib', 'typing', 'concurrent', 'time', 'ast', 'subprocess',
        'collections', 'itertools', 'functools', 'operator', 'copy',
        'pickle', 'base64', 'hashlib', 'uuid', 'random', 'math',
        'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3',
        'argparse', 'traceback'  # traceback也是标准库
    }
    
    # 本地模块
    local_modules = {
        'ctrip_detail_crawler', 'ctrip_itinerary_crawler', 
        'ctrip_booking_crawler', 'main', 'start', 'test_api'
    }
    
    return imports - stdlib_modules - local_modules

def get_package_mapping() -> Dict[str, str]:
    """import名称到包名的映射"""
    return {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn[standard]',
        'pydantic': 'pydantic', 
        'crawl4ai': 'crawl4ai',
        'httpx': 'httpx'
    }

def get_installed_versions() -> Dict[str, str]:
    """获取已安装包的版本"""
    versions = {}
    
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True)
        
        for line in result.stdout.split('\n'):
            if line and not line.startswith('Package') and not line.startswith('-'):
                parts = line.split()
                if len(parts) >= 2:
                    package = parts[0].lower()
                    version = parts[1]
                    versions[package] = version
    
    except Exception as e:
        print(f"警告: 无法获取版本信息: {e}")
    
    return versions

def main():
    """主函数"""
    
    print("🔍 分析项目依赖包...")
    print("=" * 50)
    
    # 1. 提取所有import
    all_imports = get_project_imports()
    print(f"\n📦 所有import: {sorted(all_imports)}")
    
    # 2. 过滤第三方包
    third_party = filter_third_party_packages(all_imports)
    print(f"\n🌐 第三方包: {sorted(third_party)}")
    
    # 3. 映射到实际包名
    package_mapping = get_package_mapping()
    required_packages = []
    
    for import_name in third_party:
        if import_name in package_mapping:
            required_packages.append(package_mapping[import_name])
        else:
            required_packages.append(import_name)
    
    print(f"\n📋 需要安装的包: {sorted(required_packages)}")
    
    # 4. 获取版本信息
    versions = get_installed_versions()
    
    # 5. 生成requirements.txt
    requirements_lines = [
        "# 项目依赖包",
        "# 由 generate_requirements.py 自动生成",
        ""
    ]
    
    for package in sorted(required_packages):
        package_name = package.split('[')[0].lower()
        if package_name in versions:
            version = versions[package_name]
            requirements_lines.append(f"{package}>={version}")
            print(f"✅ {package} (当前版本: {version})")
        else:
            requirements_lines.append(package)
            print(f"⚠️  {package} (未安装)")
    
    # 6. 写入文件
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(requirements_lines))
    
    print(f"\n✅ 已生成 requirements.txt")
    print(f"📁 包含 {len(required_packages)} 个依赖包")

if __name__ == "__main__":
    main() 