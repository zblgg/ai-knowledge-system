#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_engineering_rules —— UserPromptSubmit hook，每轮注入「交付军规」精简提醒。

纯静态、零依赖：不联网、不读 env、不读文件、几乎不会失败。
比 session_init.py / fetch_feishu.py 都稳（那两个依赖路径/网络/环境变量，会静默失败）。
输出包在 <engineering_rules> 标签注入给 Claude。完整标准见：
  AI知识管理系统/知识沉淀/SOP/工程交付军规.md
"""
import sys

RULES = """<engineering_rules>
【交付军规·每件事都按这个来】完整版: AI知识管理系统/知识沉淀/SOP/工程交付军规.md
做之前: ①先出分步方案+边界+边缘情况+验证法,小样本先测再全量 ②事实前提先查证(ls/grep/读)再开口
做之中: ③关键数值设合理上下界,越界大声报警别静默(把"错"变"崩") ④关键步骤留痕(日志/append-only)
交付时: ⑤数据展示 原始→处理→计算 全链路+可手算列 ⑥数据类抽样对账到可点击源
⑦【有交付物的任务必出】验收清单: ✅做好了(附自验法;涉及工具/数据管道则附"哨兵体检:几个/状态") ⚠️没做好/没做(原因) 🔍需你亲自核(具体怎么核)
云端: 任何无人值守 cron/服务必发飞书(成功失败都发,"没收到=没跑")
哨兵健康(破"谁监督哨兵"): 哨兵扁平+笨(只一层不嵌套)+一个心跳收尾(没收到=出事)终结套娃;别全改告警(警报疲劳),只聚合异常大声
铁律: 用户验收,不让用户当 QA
</engineering_rules>"""


def main():
    print(RULES)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # hook 绝不能阻断对话，任何异常都静默退出
        sys.exit(0)
