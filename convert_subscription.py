#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility for merging V2RayN subscription nodes into an existing Clash YAML
configuration.  This script decodes a V2RayN subscription (either a base64
encoded subscription blob or a plain‑text list of links), converts each
supported node into a Clash proxy dictionary using the existing
`link_to_clash` parser, and optionally inserts the new node names into
speed‑test and manual selection proxy groups within the configuration.  A
new YAML file is emitted containing the merged configuration.

Usage example::

    python convert_subscription.py subscription.txt config.yaml \
        -o merged.yaml --speedtest --manual

Where ``subscription.txt`` contains either the raw v2rayN subscription
string (base64 encoded) or one URI per line (e.g. ``vless://...``).

The script will decode the subscription, parse each link into a proxy
dictionary, append the proxies to the ``proxies`` section of the YAML, and
append the proxy names to appropriate proxy groups.  Groups of type
``url-test`` (commonly used for speed‑testing) will receive the new
nodes when ``--speedtest`` is supplied, and groups of type ``select`` (used
for manual proxy switching) will receive the new nodes when ``--manual`` is
supplied.  If no group options are given the proxies are only appended to
the ``proxies`` list and not to any groups.

Note that this tool preserves most of the existing YAML structure,
including comments and formatting, thanks to ``ruamel.yaml``.  It avoids
adding duplicate names to group lists.  Unsupported link types are skipped.
"""

import argparse
import base64
import logging
import os
import sys
from typing import Iterable, List, Optional

# ─────────────────── YAML import & fallback ────────────────────
try:
    from ruamel.yaml import YAML            # type: ignore

    _have_ruamel: bool = True

    def _new_yaml():                        # type: ignore
        y = YAML()
        y.preserve_quotes = True
        y.indent(mapping=2, sequence=4, offset=2)
        y.default_flow_style = False
        y.allow_unicode = True
        return y

except ModuleNotFoundError:                 # pragma: no cover
    import yaml as _pyyaml                  # type: ignore

    _have_ruamel = False

    def _new_yaml():                        # type: ignore
        class _Shim:
            @staticmethod
            def load(stream):
                return _pyyaml.safe_load(stream)

            @staticmethod
            def dump(data, stream):
                _pyyaml.safe_dump(
                    data, stream,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        return _Shim

try:
    from converters import link_to_clash  # type: ignore
except ImportError:
    # When executed as a standalone script outside of the package
    # hierarchy the import might fail.  In that case adjust the
    # import path relative to this file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    sys.path.insert(0, parent_dir)
    from converters import link_to_clash  # type: ignore  # noqa: E402


def parse_subscription(content: str) -> List[str]:
    """Interpret a v2rayN subscription payload.

    The subscription may be supplied as a base64 encoded blob or as a
    sequence of URI lines.  This function attempts to decode the
    payload as base64 first; if that fails it falls back to treating
    the input as plain text with one link per line.

    :param content: Subscription content.
    :return: List of individual node URIs.
    """
    content = content.strip()
    if not content:
        return []
    # Attempt base64 decode
    try:
        # Some subscription servers include whitespace or newline in
        # the base64 encoded payload; remove any whitespace first.
        normalized = "".join(content.split())
        decoded = base64.b64decode(normalized).decode("utf-8", errors="replace")
        # The decoded subscription typically contains URIs separated by
        # newlines or carriage returns.
        lines = [line.strip() for line in decoded.splitlines() if line.strip()]
        # Heuristically determine if decoding was correct by checking if
        # all lines contain the scheme delimiter.  If none of the lines
        # appear to be valid URIs we assume the input was already plain
        # text.
        if any("://" in line for line in lines):
            return lines
    except Exception:
        # If base64 decoding fails, it's likely plain text, but we log it just in case.
        logging.warning("Could not decode subscription as base64, falling back to plain text.", exc_info=True)
        pass
    # Fall back to treating the input as plain text with one URI per line
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return lines


def convert_links_to_proxies(links: Iterable[str]) -> List[dict]:
    """Convert each subscription link into a Clash proxy dictionary.

    :param links: Iterable of V2Ray/VLESS/VMess/Trojan links.
    :return: List of proxy dictionaries compatible with Clash.
    """
    proxies: List[dict] = []
    for link in links:
        proxy = link_to_clash(link)
        if proxy is not None:               # 过滤不支持/解析失败的链接
            proxies.append(proxy)
    return proxies


def update_yaml(
    config_path: str,
    proxies: List[dict],
    add_to_speedtest: bool = False,
    add_to_manual: bool = False,
    output_path: Optional[str] = None,
) -> str:
    """Merge proxies into a Clash configuration file.

    This function loads the existing YAML configuration, appends the
    supplied proxies to the ``proxies`` list, and optionally appends
    the proxy names into speed‑test and manual selection proxy groups.

    :param config_path: Path to the existing Clash YAML configuration.
    :param proxies: List of proxy dictionaries to append.
    :param add_to_speedtest: Whether to add proxy names to all
        ``url-test``/``fallback``/``load-balance`` groups.
    :param add_to_manual: Whether to add proxy names to all ``select``
        groups.
    :param output_path: Path to write the merged YAML file.  If not
        provided a file named ``new_config.yaml`` is created in the same
        directory as ``config_path``.
    :return: The path to the newly written YAML file.
    """
    # Load the existing configuration using ruamel.yaml if available,
    # otherwise fall back to PyYAML.  The ruamel loader preserves
    # comments and quoting whereas PyYAML does not.
    # 单一 YAML 实例，自动适配 ruamel 或 PyYAML
    yaml = _new_yaml()
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.load(f) or {}

    # Ensure there is a proxies section
    proxies_section = data.get("proxies")
    if proxies_section is None:
        data["proxies"] = proxies_section = []

    if not isinstance(proxies_section, list):
        raise TypeError(
            f"Expected 'proxies' to be a list, got {type(proxies_section).__name__}"
        )

    # Append new proxies to the proxies section
    for p in proxies:
        proxies_section.append(p)

    # Add proxy names to groups based on type
    if add_to_speedtest or add_to_manual:
        groups = data.get("proxy-groups", [])
        if not isinstance(groups, list):
            raise TypeError(
                f"Expected 'proxy-groups' to be a list, got {type(groups).__name__}"
            )
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_type = str(group.get("type", "")).lower()
            group_proxies = group.get("proxies")
            if not isinstance(group_proxies, list):
                continue
            # Determine if this group qualifies for insertion
            is_speed_group = group_type in {"url-test", "fallback", "load-balance"}
            is_manual_group = group_type == "select"
            names_to_add: List[str] = []
            if add_to_speedtest and is_speed_group:
                names_to_add = [p["name"] for p in proxies]
            elif add_to_manual and is_manual_group:
                names_to_add = [p["name"] for p in proxies]
            # Append names that are not already present
            for name in names_to_add:
                if name not in group_proxies:
                    group_proxies.append(name)

    # Determine output file path
    if not output_path:
        base, ext = os.path.splitext(config_path)
        output_path = f"{base}_merged{ext or '.yaml'}"

    # Write the updated configuration
    # Write the updated configuration
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return output_path


def generate_individual_yaml_files(
    proxies: List[dict],
    output_dir: str,
    template_path: Optional[str] = None,
    template_data: Optional[dict] = None,
) -> List[str]:
    """为每个代理节点生成独立的YAML配置文件。

    :param proxies: 代理节点列表
    :param output_dir: 输出目录路径
    :param template_path: 模版YAML文件的路径 (可选)
    :param template_data: 模版数据字典 (可选)
    :return: 生成的文件路径列表
    """
    import os
    import io
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载模版文件
    yaml = _new_yaml()
    if template_data is None:
        if not template_path:
            raise ValueError("Either template_path or template_data must be provided.")
        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.load(f) or {}

    # 使用深拷贝来避免YAML格式问题
    import copy
    
    generated_files = []
    
    for proxy in proxies:
        # 为每个代理创建一个新的、干净的配置对象副本
        config_data = copy.deepcopy(template_data)
        
        # 确保有proxies和proxy-groups部分
        if "proxies" not in config_data:
            config_data["proxies"] = []
        if "proxy-groups" not in config_data:
            config_data["proxy-groups"] = []
        
        # 安全地更新proxies列表
        config_data["proxies"] = [proxy]
        
        # 更新proxy-groups中的代理列表
        for group in config_data.get("proxy-groups", []):
            if isinstance(group, dict) and "proxies" in group:
                # 保留DIRECT等特殊代理，并添加当前代理名称
                group_proxies = group["proxies"]
                # 移除之前可能存在的其他代理名称，只保留DIRECT等系统代理
                system_proxies = [p for p in group_proxies if p in ["DIRECT", "REJECT", "PASS"]]
                
                # 安全地更新组的proxies列表
                group["proxies"] = system_proxies + [proxy["name"]]

        # 确保rules列表格式正确 - 完全重建rules部分
        if "rules" in config_data and isinstance(config_data.get("rules"), list):
            # 获取原始规则列表的内容
            original_rules = list(config_data["rules"])
            # 删除原有的rules键
            del config_data["rules"]
            # 重新添加rules键和值
            config_data["rules"] = original_rules
        
        # 生成文件名（清理特殊字符）
        safe_name = "".join(c for c in proxy["name"] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        if not safe_name:
            safe_name = f"proxy_{len(generated_files) + 1}"
        
        output_file = os.path.join(output_dir, f"{safe_name}.yaml")
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        original_output_file = output_file
        while os.path.exists(output_file):
            base, ext = os.path.splitext(original_output_file)
            output_file = f"{base}_{counter}{ext}"
            counter += 1
        
        # 写入文件 - 使用YAML库来正确处理代理配置
        with open(output_file, "w", encoding="utf-8") as f:
            # 在转储前添加一个空行以提高可读性
            if 'proxies' in config_data:
                config_data.yaml_set_comment_before_after_key('proxies', before='\n')
            if 'rules' in config_data:
                config_data.yaml_set_comment_before_after_key('rules', before='\n')
            
            # 先将配置写入字符串
            import io
            temp_stream = io.StringIO()
            yaml.dump(config_data, temp_stream)
            yaml_content = temp_stream.getvalue()
            
            # 修复rules格式问题
            yaml_content = yaml_content.replace('rules:   -', 'rules:\n  -')
            yaml_content = yaml_content.replace('rules:\n  -\n    ', 'rules:\n  - ')
            
            f.write(yaml_content)
        
        generated_files.append(output_file)
        logging.info(f"Generated individual config file: {output_file}")
    
    return generated_files


def read_subscription_input(path_or_data: str) -> str:
    """Read subscription data from a file path or directly from a string.

    If ``path_or_data`` corresponds to an existing file path it is read
    from disk; otherwise the string itself is treated as the subscription
    content.

    :param path_or_data: Path to a file or raw subscription content.
    :return: The content of the subscription.
    """
    if os.path.exists(path_or_data):
        with open(path_or_data, "r", encoding="utf-8") as f:
            return f.read()
    return path_or_data


def main(argv: Optional[List[str]] = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        description="Merge V2RayN subscription nodes into a Clash YAML configuration."
    )
    parser.add_argument(
        "subscription",
        help=(
            "Path to a file containing the subscription or the subscription string itself. "
            "The script will attempt to detect base64 encoded input."
        ),
    )
    parser.add_argument(
        "config",
        help="Path to the existing Clash YAML configuration to update.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Destination path for the merged configuration.  If omitted a new file with '_merged' appended to the name will be created.",
    )
    parser.add_argument(
        "--speedtest",
        action="store_true",
        help="Add the new proxy names to all URL test / fallback / load-balance groups.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Add the new proxy names to all select (manual selection) groups.",
    )
    args = parser.parse_args(argv)

    sub_content = read_subscription_input(args.subscription)
    links = parse_subscription(sub_content)
    if not links:
        sys.stderr.write("No valid links found in the subscription input.\n")
        return 1

    proxies = convert_links_to_proxies(links)
    if not proxies:
        sys.stderr.write("No supported nodes were parsed from the subscription.\n")
        return 1

    output_path = update_yaml(
        args.config,
        proxies,
        add_to_speedtest=args.speedtest,
        add_to_manual=args.manual,
        output_path=args.output,
    )
    print(f"Merged configuration saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())