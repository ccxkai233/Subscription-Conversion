import base64
import json
import logging
import urllib.parse

def vless_to_clash(link: str) -> dict:
    """
    将 VLESS 链接转换为 Clash 配置字典。
    """
    try:
        link, *tag = link.split("#", 1)
        name = urllib.parse.unquote(tag[0]) if tag else "VLESS_Node"
        u = urllib.parse.urlparse(link)
        uuid = u.username
        server = u.hostname
        port = u.port
        qs = urllib.parse.parse_qs(u.query)
        
        def q(key, default=None):
            return qs.get(key, [default])[0]

        proxy = {
            "name": name, "type": "vless", "server": server, "port": port,
            "udp": True, "uuid": uuid, "network": q("type", "tcp"),
            "tls": q("security") in ["tls", "reality"],
            "encryption": q("encryption", "none")
        }

        # 添加 flow 参数支持
        if "flow" in qs:
            proxy["flow"] = q("flow")

        # 优先从 'host' 参数获取伪装域名
        ws_host = q("host")
        
        # 根据 Clash.Meta 最新规范调整 REALITY 和 TLS 参数
        # servername (sni) 和 client-fingerprint (fp) 移至顶级
        if proxy.get("tls"):
            # 如果有 ws_host，优先使用它作为 servername (SNI)
            # 否则，使用 'sni' 参数，如果还没有，则回退到 server 地址
            proxy["servername"] = ws_host or q("sni", server)
        
        if "fp" in qs:
            proxy["client-fingerprint"] = q("fp")

        if q("security") == "reality":
            proxy["reality-opts"] = {
                "public-key": q("pbk"),
                "short-id": q("sid", "")
            }
        
        if proxy["network"] == "ws":
            # 如果有 ws_host，用它作为 Host 头部
            # 否则，回退到 server 地址
            proxy["ws-opts"] = {
                "path": q("path", "/"),
                "headers": {"Host": ws_host or server}
            }
        
        if proxy["network"] == "grpc":
            proxy["grpc-opts"] = {"grpc-service-name": q("serviceName", "")}
            
        return proxy
    except Exception:
        logging.warning(f"Failed to parse VLESS link: {link}", exc_info=True)
        return None

def vmess_to_clash(link: str) -> dict:
    """
    将 VMess 链接转换为 Clash 配置字典。
    """
    try:
        # VMess 链接是 base64 编码的 JSON
        decoded_part = base64.b64decode(link.split("vmess://")[1]).decode('utf-8')
        vmess_data = json.loads(decoded_part)

        proxy = {
            "name": vmess_data.get("ps", "VMess_Node"),
            "type": "vmess",
            "server": vmess_data.get("add"),
            "port": vmess_data.get("port"),
            "uuid": vmess_data.get("id"),
            "alterId": vmess_data.get("aid"),
            "cipher": vmess_data.get("scy", "auto"),
            "udp": True,
            "network": vmess_data.get("net", "tcp"),
            "tls": vmess_data.get("tls") == "tls",
        }

        if proxy["tls"]:
            proxy["servername"] = vmess_data.get("sni", vmess_data.get("add"))

        if proxy["network"] == "ws":
            proxy["ws-opts"] = {
                "path": vmess_data.get("path", "/"),
                "headers": {"Host": vmess_data.get("host", vmess_data.get("add"))}
            }
        
        if proxy["network"] == "grpc":
            proxy["grpc-opts"] = {"grpc-service-name": vmess_data.get("path", "")}

        return proxy
    except Exception:
        logging.warning(f"Failed to parse VMess link: {link}", exc_info=True)
        return None

def trojan_to_clash(link: str) -> dict:
    """
    将 Trojan 链接转换为 Clash 配置字典。
    """
    try:
        link, *tag = link.split("#", 1)
        name = urllib.parse.unquote(tag[0]) if tag else "Trojan_Node"
        u = urllib.parse.urlparse(link)
        
        proxy = {
            "name": name,
            "type": "trojan",
            "server": u.hostname,
            "port": u.port,
            "password": u.username,
            "udp": True,
            "sni": urllib.parse.parse_qs(u.query).get("sni", [u.hostname])[0]
        }
        
        return proxy
    except Exception:
        logging.warning(f"Failed to parse Trojan link: {link}", exc_info=True)
        return None

# ──────────────────  Shadowsocks  (ss://) 解析  ──────────────────
def ss_to_clash(link: str) -> dict | None:
    """
    Convert a Shadowsocks ss:// URI (SIP002) to a Clash proxy dict.
    Supports both plain & base64‑encoded forms.
    """
    import base64, urllib.parse
    try:
        uri = link[5:] if link.startswith("ss://") else None
        if uri is None:
            return None

        # handle optional tag
        if "#" in uri:
            uri, tag = uri.split("#", 1)
            name = urllib.parse.unquote(tag)
        else:
            name = "SS_Node"

        # two possible layouts
        if "@" in uri:
            enc_cred, server_port = uri.split("@", 1)
            method, password = base64.urlsafe_b64decode(enc_cred + "==").decode().split(":", 1)
        else:
            decoded = base64.urlsafe_b64decode(uri + "==").decode()
            method, rest = decoded.split(":", 1)
            password, server_port = rest.split("@", 1)

        server, port = server_port.split(":", 1)
        return {
            "name": name,
            "type": "ss",
            "server": server,
            "port": int(port),
            "cipher": method,
            "password": password,
        }
    except Exception:                       # pragma: no cover
        return None

# 协议解析器适配器表
PARSERS = {
    "vless": vless_to_clash,
    "vmess": vmess_to_clash,
    "trojan": trojan_to_clash,
    "ss": ss_to_clash,
}

def link_to_clash(link: str) -> dict | None:
    """
    自动识别协议并调用相应的解析器。
    
    :param link: 节点链接字符串 (e.g., "vless://...", "vmess://...", "trojan://...")
    :return: Clash 配置字典，如果协议不支持或解析失败则返回 None
    """
    if not isinstance(link, str):
        return None
        
    try:
        protocol = link.split("://")[0].lower()
        parser = PARSERS.get(protocol)
        
        if parser:
            return parser(link)
        else:
            return None
    except IndexError:
        # 如果链接格式不正确（例如，不包含 "://"），则返回 None
        logging.warning(f"Invalid link format (missing '://'): {link}")
        return None