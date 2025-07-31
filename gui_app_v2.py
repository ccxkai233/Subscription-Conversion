# 如果未安装 customtkinter, 请先运行: pip install customtkinter
# pip install ruamel.yaml
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import logging
from ruamel.yaml import YAML
import io
import textwrap
import copy

# Import helper functions from the conversion module
try:
    from .convert_subscription import (
        parse_subscription,
        convert_links_to_proxies,
        update_yaml,
        generate_individual_yaml_files,
    )
except ImportError:
    from convert_subscription import (
        parse_subscription,
        convert_links_to_proxies,
        update_yaml,
        generate_individual_yaml_files,
    )
from converters import link_to_clash

class ProxyGroup:
    """代理组类，用于管理测速组和对应的手动选择节点"""
    def __init__(self, name, proxies=None):
        self.name = name
        self.proxies = proxies or []
        self.manual_node_name = f"🚀 {name}"

class ClashConfigApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        logging.info("Clash Config App v2 starting up...")

        self.title("Clash 配置生成器 v2.0")
        self.geometry("1500x900")
        
        # YAML 处理器
        self.yaml_rt = YAML()
        self.yaml_rt.preserve_quotes = True
        self.yaml_rt.indent(mapping=2, sequence=4, offset=2)
        
        # 当前配置数据
        self.config_data = {}
        self.template_loaded = False
        
        # 代理组管理
        self.proxy_groups = []  # ProxyGroup 对象列表
        self.group_widgets = []  # 对应的UI组件列表
        
        self.setup_ui()
        self.on_output_mode_change() # 设置初始UI状态
        
    def setup_ui(self):
        """设置用户界面"""
        # 主容器配置
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 顶部工具栏
        self.create_toolbar()
        
        # 主要内容区域
        self.create_main_content()
        
    def create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = ctk.CTkFrame(self, height=60)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        toolbar.grid_columnconfigure(1, weight=1)
        
        # 导入模版按钮
        self.import_template_btn = ctk.CTkButton(
            toolbar, 
            text="📁 导入模版", 
            command=self.import_template,
            width=120
        )
        self.import_template_btn.grid(row=0, column=0, padx=10, pady=10)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            toolbar, 
            text="请先导入模版文件", 
            text_color=("gray60", "gray40")
        )
        self.status_label.grid(row=0, column=1, padx=20, pady=10, sticky="w")
        
        # 输出选项
        self.output_mode_var = ctk.StringVar(value="merged")
        self.output_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        self.output_frame.grid(row=0, column=2, padx=10, pady=10)
        
        ctk.CTkLabel(self.output_frame, text="输出模式:").grid(row=0, column=0, padx=(0, 10))
        
        self.single_file_radio = ctk.CTkRadioButton(
            self.output_frame,
            text="单一文件",
            variable=self.output_mode_var,
            value="merged",
            command=self.on_output_mode_change
        )
        self.single_file_radio.grid(row=0, column=1, padx=5)
        
        self.individual_radio = ctk.CTkRadioButton(
            self.output_frame,
            text="独立文件",
            variable=self.output_mode_var,
            value="individual",
            command=self.on_output_mode_change
        )
        self.individual_radio.grid(row=0, column=2, padx=5)
        
    def create_main_content(self):
        """创建主要内容区域"""
        # 左侧配置面板
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(5, 10))
        self.left_panel.grid_columnconfigure(0, weight=1)
        
        # 右侧预览面板
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(5, 10))
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)
        
        self.create_left_panel()
        self.create_right_panel()
        
    def create_left_panel(self):
        """创建左侧配置面板"""
        # 标题
        title_label = ctk.CTkLabel(
            self.left_panel, 
            text="📋 Clash 配置编辑器", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(15, 10), sticky="w", padx=15)
        
        # 滚动框架
        self.config_scroll = ctk.CTkScrollableFrame(self.left_panel)
        self.config_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.config_scroll.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=1)
        
        # DNS 配置区域
        self.create_dns_section()
        
        # 代理组配置区域
        self.create_proxy_groups_section()

        # 手动选择组区域
        self.create_manual_group_section()
        
        # 规则配置区域
        self.create_rules_section()
        
        # 操作按钮
        self.create_action_buttons()
        
    def create_dns_section(self):
        """创建 DNS 配置区域"""
        dns_frame = ctk.CTkFrame(self.config_scroll)
        dns_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15), padx=5)
        dns_frame.grid_columnconfigure(1, weight=1)
        
        # DNS 标题
        dns_title = ctk.CTkLabel(
            dns_frame, 
            text="🌐 DNS 配置", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        dns_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))
        
        # DNS 配置文本框
        self.dns_textbox = ctk.CTkTextbox(dns_frame, height=120)
        self.dns_textbox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        
    def create_proxy_groups_section(self):
        """创建代理组配置区域"""
        self.groups_frame = ctk.CTkFrame(self.config_scroll)
        self.groups_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15), padx=5)
        self.groups_frame.grid_columnconfigure(0, weight=1)
        
        # 代理组标题和控制按钮
        header_frame = ctk.CTkFrame(self.groups_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        groups_title = ctk.CTkLabel(
            header_frame, 
            text="🚀 代理组配置", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        groups_title.grid(row=0, column=0, sticky="w")
        
        self.add_group_btn = ctk.CTkButton(
            header_frame,
            text="➕ 添加测速组",
            command=self.add_proxy_group,
            width=100,
            height=28
        )
        self.add_group_btn.grid(row=0, column=1, padx=(10, 0))
        
        # 代理组容器
        self.groups_container = ctk.CTkFrame(self.groups_frame, fg_color="transparent")
        self.groups_container.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.groups_container.grid_columnconfigure(0, weight=1)
        
        # 添加第一个默认组
        self.add_proxy_group()
        
        # 此调用已移至 create_left_panel
        
    def add_proxy_group(self):
        """添加新的代理组"""
        group_index = len(self.proxy_groups)
        group_name = f"测速组{group_index + 1}"
        
        # 创建代理组对象
        proxy_group = ProxyGroup(group_name)
        self.proxy_groups.append(proxy_group)
        
        # 创建UI组件
        group_widget = self.create_group_widget(self.groups_container, group_index, proxy_group)
        self.group_widgets.append(group_widget)
        
        # 更新预览
        if self.template_loaded:
            self.update_preview()
            
    def create_group_widget(self, parent, index, proxy_group):
        """创建单个代理组的UI组件"""
        group_frame = ctk.CTkFrame(parent)
        group_frame.grid(row=index, column=0, sticky="ew", pady=(0, 10))
        group_frame.grid_columnconfigure(1, weight=1)
        
        # 组标题和删除按钮
        header_frame = ctk.CTkFrame(group_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(15, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # 组名输入
        name_label = ctk.CTkLabel(header_frame, text="组名:", font=ctk.CTkFont(weight="bold"))
        name_label.grid(row=0, column=0, sticky="w")
        
        name_entry = ctk.CTkEntry(header_frame, width=150)
        name_entry.grid(row=0, column=1, padx=(10, 0), sticky="w")
        name_entry.insert(0, proxy_group.name)
        name_entry.bind('<KeyRelease>', lambda e: self.on_group_name_change(index, name_entry.get()))
        
        # 删除按钮
        if len(self.proxy_groups) > 1:  # 至少保留一个组
            def remove_wrapper(idx=index):
                self.remove_proxy_group(idx)

            delete_btn = ctk.CTkButton(
                header_frame,
                text="🗑️",
                command=remove_wrapper,
                width=30,
                height=28,
                fg_color="red",
                hover_color="darkred"
            )
            delete_btn.grid(row=0, column=2, padx=(10, 0))
        
        # 订阅链接输入
        ctk.CTkLabel(
            group_frame, 
            text=f"⚡ {proxy_group.name} 订阅链接:", 
            font=ctk.CTkFont(weight="bold")
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 5))
        
        textbox = ctk.CTkTextbox(group_frame, height=80)
        textbox.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))
        textbox.bind('<KeyRelease>', lambda e: self.on_subscription_change())
        
        # 添加占位符文本
        placeholder_text = f"输入{proxy_group.name}的订阅链接，每行一个...\n例如：\nvless://...\nvmess://...\ntrojan://..."
        textbox.insert("1.0", placeholder_text)
        textbox.configure(text_color=("gray60", "gray40"))
        
        def clear_placeholder_wrapper(event, tb=textbox, pt=placeholder_text):
            self.clear_placeholder(tb, pt)
            
        textbox.bind('<FocusIn>', clear_placeholder_wrapper)
        
        # 手动选择节点预览
        preview_label = ctk.CTkLabel(
            group_frame,
            text=f"👆 对应手动选择节点: {proxy_group.manual_node_name}",
            font=ctk.CTkFont(size=12),
            text_color=("blue", "lightblue")
        )
        preview_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 15))
        
        return {
            'frame': group_frame,
            'name_entry': name_entry,
            'textbox': textbox,
            'preview_label': preview_label
        }
        
    def remove_proxy_group(self, index):
        """删除代理组"""
        if len(self.proxy_groups) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个代理组")
            return
            
        # 删除数据和UI组件
        del self.proxy_groups[index]
        self.group_widgets[index]['frame'].destroy()
        del self.group_widgets[index]
        
        # 重新创建所有组的UI以确保索引正确
        self.recreate_all_group_widgets()
            
        # 更新预览
        if self.template_loaded:
            self.update_preview()

    def recreate_all_group_widgets(self):
        """重新创建所有代理组的UI组件"""
        # 清空现有的UI
        for widget in self.group_widgets:
            widget['frame'].destroy()
        self.group_widgets.clear()

        # 根据数据重新创建UI
        for i, proxy_group in enumerate(self.proxy_groups):
            group_widget = self.create_group_widget(self.groups_container, i, proxy_group)
            self.group_widgets.append(group_widget)
            
    def on_group_name_change(self, index, new_name):
        """组名改变时的回调"""
        if index < len(self.proxy_groups):
            self.proxy_groups[index].name = new_name
            self.proxy_groups[index].manual_node_name = f"🚀 {new_name}"
            
            # 更新预览标签
            if index < len(self.group_widgets):
                self.group_widgets[index]['preview_label'].configure(
                    text=f"👆 对应手动选择节点: {self.proxy_groups[index].manual_node_name}"
                )
                
            # 更新预览
            if self.template_loaded:
                self.update_preview()

    def create_manual_group_section(self):
        """创建手动输入区域"""
        self.manual_frame = ctk.CTkFrame(self.config_scroll)
        self.manual_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15), padx=5)
        self.manual_frame.grid_columnconfigure(0, weight=1)

        # 标题
        self.manual_title_label = ctk.CTkLabel(
            self.manual_frame,
            text="👆 手动选择组订阅",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.manual_title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        # 订阅链接输入
        self.manual_textbox = ctk.CTkTextbox(self.manual_frame, height=150)
        self.manual_textbox.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.manual_textbox.bind('<KeyRelease>', lambda e: self.on_subscription_change())

        # 添加占位符文本
        placeholder_text = "输入订阅链接或节点，每行一个..."
        self.manual_textbox.insert("1.0", placeholder_text)
        self.manual_textbox.configure(text_color=("gray60", "gray40"))
        
        def clear_placeholder_wrapper(event, tb=self.manual_textbox, pt=placeholder_text):
            self.clear_placeholder(tb, pt)
            
        self.manual_textbox.bind('<FocusIn>', clear_placeholder_wrapper)
        
    def create_rules_section(self):
        """创建规则配置区域"""
        rules_frame = ctk.CTkFrame(self.config_scroll)
        rules_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15), padx=5)
        rules_frame.grid_columnconfigure(1, weight=1)
        
        # 规则标题
        rules_title = ctk.CTkLabel(
            rules_frame, 
            text="📜 规则配置", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        rules_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))
        
        # 规则配置文本框
        self.rules_textbox = ctk.CTkTextbox(rules_frame, height=150)
        self.rules_textbox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        
    def create_action_buttons(self):
        """创建操作按钮"""
        button_frame = ctk.CTkFrame(self.config_scroll, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", pady=15, padx=5)
        button_frame.grid_columnconfigure(0, weight=1)
        
        self.action_btn = ctk.CTkButton(
            button_frame,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.action_btn.grid(row=0, column=0, sticky="ew")
        
    def create_right_panel(self):
        """创建右侧预览面板"""
        # 标题
        preview_title = ctk.CTkLabel(
            self.right_panel, 
            text="👁️ 配置预览", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        preview_title.grid(row=0, column=0, pady=(15, 10), sticky="w", padx=15)
        
        # 预览文本框
        self.preview_textbox = ctk.CTkTextbox(
            self.right_panel, 
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.preview_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # 底部操作栏
        bottom_frame = ctk.CTkFrame(self.right_panel, height=50, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        self.copy_btn = ctk.CTkButton(
            bottom_frame,
            text="📋 复制到剪贴板",
            command=self.copy_to_clipboard,
            width=150
        )
        self.copy_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.line_count_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            text_color=("gray60", "gray40")
        )
        self.line_count_label.grid(row=0, column=1, sticky="e")
        
    def clear_placeholder(self, textbox, placeholder_text):
        """清除占位符文本"""
        current_text = textbox.get("1.0", "end-1c")
        if current_text == placeholder_text:
            textbox.delete("1.0", "end")
            textbox.configure(text_color=("black", "white"))
            
    def import_template(self):
        """导入模版文件"""
        # 首先尝试使用默认模版
        default_template = "模版.yaml"
        if os.path.exists(default_template):
            if messagebox.askyesno("导入模版", f"发现默认模版文件 '{default_template}'，是否使用？"):
                self.load_template_file(default_template)
                return
        
        # 让用户选择模版文件
        file_path = filedialog.askopenfilename(
            title="选择 Clash 配置模版",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_template_file(file_path)
            
    def load_template_file(self, file_path):
        """加载模版文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.config_data = self.yaml_rt.load(f) or {}

            # Ensure essential keys exist and are lists, preserving ruamel types
            for key in ['proxies', 'proxy-groups', 'rules']:
                if self.config_data.get(key) is None:
                    self.config_data[key] = []
            
            self.template_loaded = True
            self.status_label.configure(
                text=f"✅ 已加载模版: {os.path.basename(file_path)}",
                text_color=("green", "lightgreen")
            )
            
            # 填充界面
            self.populate_ui_from_config()
            self.update_preview()
            self.on_output_mode_change() # 确保加载模版后UI状态正确
            
            logging.info(f"Template loaded successfully: {file_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载模版文件失败: {e}")
            logging.error(f"Failed to load template: {e}")
            
    def populate_ui_from_config(self):
        """根据配置数据填充界面"""
        # 填充 DNS 配置
        if 'dns' in self.config_data:
            dns_yaml = io.StringIO()
            self.yaml_rt.dump({'dns': self.config_data['dns']}, dns_yaml)
            dns_content_raw = dns_yaml.getvalue().replace('dns:\n', '', 1)
            dns_content = textwrap.dedent(dns_content_raw).strip()
            self.dns_textbox.delete("1.0", "end")
            self.dns_textbox.insert("1.0", dns_content)
        
        # 填充规则配置
        if 'rules' in self.config_data:
            rules_yaml = io.StringIO()
            # Dump the list directly to get proper YAML list format
            self.yaml_rt.dump(self.config_data['rules'], rules_yaml)
            rules_content = rules_yaml.getvalue().strip()
            self.rules_textbox.delete("1.0", "end")
            self.rules_textbox.insert("1.0", rules_content)
            
    def update_config_from_ui(self):
        """从UI控件（DNS、规则等）更新 self.config_data"""
        if not self.template_loaded:
            return
        try:
            # 更新 DNS
            dns_content = self.dns_textbox.get("1.0", "end-1c").strip()
            if dns_content:
                new_dns_data = self.yaml_rt.load(dns_content)
                self.config_data['dns'] = new_dns_data

            # 更新 Rules
            rules_content = self.rules_textbox.get("1.0", "end-1c").strip()
            if rules_content:
                new_rules_data = self.yaml_rt.load(rules_content)
                if isinstance(new_rules_data, list):
                    # 强制设置新列表的样式，这是修复问题的关键
                    try:
                        new_rules_data.fa.set_block_style()
                    except AttributeError:
                        # 如果没有fa属性，创建一个新的CommentedSeq
                        from ruamel.yaml.comments import CommentedSeq
                        temp_rules = CommentedSeq(new_rules_data)
                        temp_rules.fa.set_block_style()
                        new_rules_data = temp_rules
                # 用设置好格式的新对象，替换掉旧的对象
                self.config_data['rules'] = new_rules_data
        except Exception as e:
            logging.error(f"Failed to update config from UI: {e}")
            messagebox.showerror("错误", f"解析UI中的配置时出错: {e}")

    def on_subscription_change(self, event=None):
        """订阅链接改变时的回调"""
        if self.template_loaded:
            # 在单一文件模式下实时生成配置
            if self.output_mode_var.get() == "merged":
                self.generate_config()
            else:
                self.update_preview()
            
    def on_output_mode_change(self):
        """输出模式改变时的回调"""
        mode = self.output_mode_var.get()
        
        # 默认显示所有内容
        self.groups_frame.grid()
        self.manual_frame.grid()
        self.right_panel.grid()
        self.left_panel.grid_configure(columnspan=1)
        if hasattr(self, 'action_btn'):
            self.action_btn.configure(state="normal")

        if mode == "individual":
            # 独立文件模式：隐藏测速组和预览
            self.groups_frame.grid_remove()
            self.right_panel.grid_remove()
            self.left_panel.grid_configure(columnspan=2)
            if hasattr(self, 'manual_title_label'):
                self.manual_title_label.configure(text="📄 独立文件节点订阅 (每行一个)")
            if hasattr(self, 'action_btn'):
                self.action_btn.configure(text="💾 导出独立文件", command=self.export_config)
        
        elif mode == "merged":
            # 单一文件模式：恢复默认视图
            if hasattr(self, 'manual_title_label'):
                self.manual_title_label.configure(text="👆 手动选择组订阅")
            if hasattr(self, 'action_btn'):
                self.action_btn.configure(text="💾 导出单一文件", command=self.export_merged_file)

        # 确保在加载模版前调用时不会出错
        if hasattr(self, 'template_loaded') and self.template_loaded:
            self.update_preview()
        
    def generate_config(self):
        """生成配置"""
        self.update_config_from_ui()  # 从UI更新配置
        if not self.template_loaded:
            messagebox.showwarning("警告", "请先导入模版文件")
            return
            
        try:
            all_proxies = []
            manual_proxies = []

            # 处理每个动态代理组（测速组）
            for i, (proxy_group, widget) in enumerate(zip(self.proxy_groups, self.group_widgets)):
                content = widget['textbox'].get("1.0", "end-1c").strip()
                
                if content and not content.startswith("输入"):  # 排除占位符文本
                    links = []
                    for line in content.splitlines():
                        line = line.strip()
                        if line:
                            if line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://')):
                                links.append(line)
                            else:
                                links.extend(parse_subscription(line))
                    
                    proxies = convert_links_to_proxies(links)
                    proxy_group.proxies = proxies
                    all_proxies.extend(proxies)
                else:
                    # 如果输入框为空或只有占位符，清空该组的代理
                    proxy_group.proxies = []

            # 处理固定的手动选择组
            manual_content = self.manual_textbox.get("1.0", "end-1c").strip()
            if manual_content and not manual_content.startswith("输入"):
                manual_links = []
                for line in manual_content.splitlines():
                    line = line.strip()
                    if line:
                        if line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://')):
                            manual_links.append(line)
                        else:
                            manual_links.extend(parse_subscription(line))
                
                manual_proxies = convert_links_to_proxies(manual_links)
                all_proxies.extend(manual_proxies)
            
            # 更新配置数据（即使没有代理也要更新，以清空之前的数据）
            self.update_config_with_proxy_groups(manual_proxies)
            self.update_preview()
            
            if all_proxies:
                total_speed_groups = len([g for g in self.proxy_groups if g.proxies])
                self.status_label.configure(
                    text=f"✅ 已生成 {len(all_proxies)} 个节点 (测速组: {total_speed_groups}, 手动: {len(manual_proxies)})",
                    text_color=("green", "lightgreen")
                )
            else:
                self.status_label.configure(
                    text="⚠️ 没有解析到有效的代理节点",
                    text_color=("orange", "orange")
                )
            
        except Exception as e:
            messagebox.showerror("错误", f"生成配置失败: {e}")
            logging.error(f"Failed to generate config: {e}")
            
    def update_config_with_proxy_groups(self, manual_proxies):
        """使用代理组更新配置"""
        # 1. 收集所有代理节点
        all_proxies = []
        for group in self.proxy_groups:
            all_proxies.extend(group.proxies)
        all_proxies.extend(manual_proxies)
        
        # 安全地更新 proxies 列表，以保留格式
        if 'proxies' not in self.config_data:
            self.config_data['proxies'] = []
        self.config_data['proxies'].clear()
        self.config_data['proxies'].extend(all_proxies)

        # 2. 从模版中分离出主选择组和其他基础组
        main_select_group = None
        other_base_groups = []
        if 'proxy-groups' in self.config_data:
            # 创建一个副本进行迭代，因为我们会修改原始列表
            for group in list(self.config_data['proxy-groups']):
                if isinstance(group, dict) and group.get('name') == '🚀 PROXY' and group.get('type') == 'select':
                    main_select_group = group
                # 过滤掉所有旧的 url-test 组
                elif isinstance(group, dict) and group.get('type') not in ['url-test', 'fallback', 'load-balance']:
                    other_base_groups.append(group)
        
        # 3. 如果模版中没有主选择组，就创建一个
        if main_select_group is None:
            main_select_group = {'name': '🚀 PROXY', 'type': 'select', 'proxies': []}

        # 4. 创建新的 url-test 组
        new_speedtest_groups = []
        for proxy_group in self.proxy_groups:
            if proxy_group.proxies:
                speedtest_group = {
                    'name': proxy_group.name,
                    'type': 'url-test',
                    'url': 'http://www.gstatic.com/generate_204',
                    'interval': 900,
                    'proxies': [p['name'] for p in proxy_group.proxies]
                }
                new_speedtest_groups.append(speedtest_group)

        # 5. 填充主选择组的 proxies 列表
        # 保留 DIRECT 等特殊条目
        final_select_proxies = [p for p in main_select_group.get('proxies', []) if p in ['DIRECT', 'REJECT']]
        # 添加新的 url-test 组的名称
        final_select_proxies.extend([g['name'] for g in new_speedtest_groups])
        # 添加手动选择的单个节点的名称
        final_select_proxies.extend([p['name'] for p in manual_proxies])
        main_select_group['proxies'] = final_select_proxies

        # 6. 合并所有组，确保主选择组在正确的位置
        final_groups = new_speedtest_groups
        # 将主选择组和其他组重新组合
        # 确保主选择组只出现一次
        other_base_groups = [g for g in other_base_groups if g.get('name') != '🚀 PROXY']
        final_groups.append(main_select_group)
        final_groups.extend(other_base_groups)
        
        # 安全地更新 proxy-groups 列表，以保留格式
        if 'proxy-groups' not in self.config_data:
            self.config_data['proxy-groups'] = []
        self.config_data['proxy-groups'].clear()
        self.config_data['proxy-groups'].extend(final_groups)
        
    def update_preview(self):
        """更新预览"""
        if not self.template_loaded:
            return
            
        try:
            # 生成完整的 YAML 预览
            preview_yaml = io.StringIO()
            self.yaml_rt.dump(self.config_data, preview_yaml)
            preview_content = preview_yaml.getvalue()
            
            # 修复预览中的rules格式问题
            preview_content = preview_content.replace('rules:   -', 'rules:\n  -')
            preview_content = preview_content.replace('rules:\n  -\n    ', 'rules:\n  - ')
            
            # 更新预览文本框
            self.preview_textbox.delete("1.0", "end")
            self.preview_textbox.insert("1.0", preview_content)
            
            # 更新行数统计
            line_count = len(preview_content.splitlines())
            self.line_count_label.configure(text=f"共 {line_count} 行")
            
        except Exception as e:
            logging.error(f"Failed to update preview: {e}")
            
    def copy_to_clipboard(self):
        """复制到剪贴板"""
        content = self.preview_textbox.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
        
        # 显示提示
        self.status_label.configure(
            text="✅ 已复制到剪贴板",
            text_color=("green", "lightgreen")
        )
        self.after(2000, lambda: self.status_label.configure(
            text="✅ 已加载模版" if self.template_loaded else "请先导入模版文件",
            text_color=("green", "lightgreen") if self.template_loaded else ("gray60", "gray40")
        ))
        
    def generate_and_export_merged(self):
        """生成配置并导出合并文件"""
        # 确保配置是最新的
        self.generate_config()
        # 检查是否有代理生成
        if self.config_data and self.config_data.get('proxies'):
            self.export_merged_file()
        else:
            messagebox.showwarning("警告", "没有解析到有效的代理节点，无法导出")
            logging.warning("No proxies generated, skipping export.")

    def export_config(self):
        """根据当前模式导出配置"""
        if not self.template_loaded:
            messagebox.showwarning("警告", "请先导入模版文件")
            return
            
        output_mode = self.output_mode_var.get()
        
        try:
            if output_mode == "individual":
                self.export_individual_files()
            elif output_mode == "merged":
                self.export_merged_file()
                
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
            logging.error(f"Failed to export config: {e}")
            
    def export_individual_files(self):
        """为每个手动输入的链接导出独立的配置文件"""
        self.update_config_from_ui()
        if not self.template_loaded:
            messagebox.showwarning("警告", "请先导入模版文件")
            return

        manual_content = self.manual_textbox.get("1.0", "end-1c").strip()
        if not manual_content or manual_content.startswith("输入"):
            messagebox.showwarning("警告", "请输入至少一个节点链接")
            return

        links = []
        for line in manual_content.splitlines():
            line = line.strip()
            if line:
                if line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://')):
                    links.append(line)
                else:
                    try:
                        links.extend(parse_subscription(line))
                    except Exception as e:
                        logging.warning(f"无法解析订阅链接 {line}: {e}")
        
        if not links:
            messagebox.showwarning("警告", "没有有效的节点链接或无法从订阅中解析节点")
            return

        output_dir = filedialog.askdirectory(title="选择独立配置文件的输出目录")
        if not output_dir:
            return

        proxies = convert_links_to_proxies(links)
        if not proxies:
            messagebox.showerror("错误", "无法从链接转换出任何代理节点")
            return

        try:
            # 直接将内存中的配置数据传递给函数
            generated_files = generate_individual_yaml_files(
                template_data=self.config_data,
                proxies=proxies,
                output_dir=output_dir
            )
            
            if generated_files:
                messagebox.showinfo(
                    "成功",
                    f"已成功导出 {len(generated_files)} 个独立配置文件到:\n{output_dir}"
                )
            else:
                messagebox.showerror("错误", "未能导出任何文件")

        except Exception as e:
            messagebox.showerror("错误", f"导出独立文件时出错: {e}")
            logging.error(f"Error during individual file export: {e}")
                
    def export_merged_file(self):
        """导出合并文件"""
        # 检查是否有有效的代理节点
        if not self.config_data.get('proxies'):
            messagebox.showwarning("警告", "没有解析到有效的代理节点，无法导出")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 直接使用字符串替换方法，避免复杂的YAML处理
                import io
                temp_stream = io.StringIO()
                self.yaml_rt.dump(self.config_data, temp_stream)
                yaml_content = temp_stream.getvalue()
                
                # 简单粗暴地修复rules格式问题
                yaml_content = yaml_content.replace('rules:   -', 'rules:\n  -')
                yaml_content = yaml_content.replace('rules:\n  -\n    ', 'rules:\n  - ')
                
                f.write(yaml_content)
                
            messagebox.showinfo("成功", f"配置文件已保存到:\n{file_path}")

if __name__ == "__main__":
    # 日志配置
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        filename="app.log",
        filemode="w",
        encoding='utf-8'
    )
    
    # 设置外观
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    app = ClashConfigApp()
    app.mainloop()