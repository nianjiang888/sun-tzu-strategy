#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
孙子·战略决策引擎（sun_tzu_engine.py）
输入一段场景/决策描述，输出：
  ① 红线判定（违法违规/恶性竞争等 → 拒绝并提示）
  ② 场景/关键词识别 → 推荐战略框架（五事七计/知己知彼/避实击虚…）
  ③ 该框架的引导问题清单 + 下一步动作（主动引导，而非只给理论）
  ④ 红线声明（非专业咨询）
仅供战略思维引导，非法律/财务/专业咨询。
"""
import sys
import os
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "resources", "strategies.json")

# 关键词 → 框架 id（口语/短词也能命中）
KEYWORDS = {
    "项目": ["F1", "F5"], "立项": ["F1"], "投资": ["F1"], "决策": ["F1", "F5"],
    "竞争": ["F2", "F3"], "对手": ["F2", "F3"], "打败": ["F3"], "差异化": ["F3"], "细分": ["F3"],
    "谈判": ["F2", "F3", "F4"], "团队": ["F7"], "管理": ["F7"], "激励": ["F7"],
    "申报": ["F2"], "资金": ["F2"], "速战": ["F5"], "快速": ["F5"], "创新": ["F6"], "营销": ["F6"],
    "战略": ["F1"], "知己知彼": ["F2"], "避实击虚": ["F3"], "以逸待劳": ["F4"],
    "五事七计": ["F1"], "奇正": ["F6"], "上下同欲": ["F7"], "SWOT": ["F2"],
}


def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def check_red_flag(text, db):
    return [w for w in db.get("red_flags", []) if w in text]


def match_scene(text, db):
    for s in db.get("scenes", []):
        if (s["scene"] in text
                or any(k in text for k in s.get("keywords", []))
                or any(k in text for k in s["use"])):
            return s
    return None


def match_frameworks(text, db):
    score = {}
    # 精确：框架名 / 场景整串
    for fw in db.get("frameworks", []):
        if fw["name"] in text:
            score[fw["id"]] = score.get(fw["id"], 0) + 2
        for sc in fw.get("scene", []):
            if sc in text:
                score[fw["id"]] = score.get(fw["id"], 0) + 1
    # 关键词层（口语/短词）
    for kw, ids in KEYWORDS.items():
        if kw in text:
            for i in ids:
                score[i] = score.get(i, 0) + 1
    fw_by_id = {f["id"]: f for f in db["frameworks"]}
    ranked = sorted(score.items(), key=lambda x: x[1], reverse=True)
    return [fw_by_id[i] for i, _ in ranked if i in fw_by_id]


def run(text, as_json=False):
    db = load_db()
    text = (text or "").strip()
    out = {"input": text}

    rf = check_red_flag(text, db)
    out["red_flag"] = rf
    if rf:
        out["verdict"] = "红线拒绝"
        out["message"] = "检测到可能涉及违规/恶意的表述（%s）。本工具仅用于合规的战略思维训练，不提供任何违法违规或损害他人权益的建议。" % "、".join(rf)
        out["action"] = "请基于合法合规的前提重新描述你的场景"
        return _emit(out, as_json)

    scene = match_scene(text, db)
    ranked = match_frameworks(text, db)
    if not scene and not ranked:
        out["verdict"] = "请明确场景"
        out["message"] = "未识别到具体场景。可说明：项目决策 / 竞争分析 / 谈判 / 团队管理 / 资金申报 等。"
        out["frameworks"] = [{"name": f["name"], "purpose": f["purpose"],
                              "guide_questions": f.get("steps", []), "output": f.get("output", "")}
                             for f in db["frameworks"]]
        out["action"] = "描述具体场景后，孙子会推荐对应框架并引导你填表"
        return _emit(out, as_json)

    rec_fw = []
    if scene:
        for fname in scene["use"]:
            fw = next((f for f in db["frameworks"] if f["name"] == fname), None)
            if fw:
                rec_fw.append(fw)
    if not rec_fw:
        rec_fw = ranked[:3]
    if not rec_fw:
        rec_fw = db["frameworks"][:1]

    out["verdict"] = "推荐框架"
    out["scene"] = scene["scene"] if scene else None
    out["scene_tip"] = scene.get("tip") if scene else None
    blocks = []
    for fw in rec_fw:
        blocks.append({
            "name": fw["name"],
            "purpose": fw["purpose"],
            "guide_questions": fw.get("steps", []),
            "output": fw.get("output", ""),
        })
    out["frameworks"] = blocks
    out["redline"] = "本工具为战略思维引导，非法律/财务/专业咨询；重大经营与投资决策须结合实际并咨询专业顾问。"
    out["action"] = "按引导问题逐项填答，或让孙子帮你生成对应模板方案"
    return _emit(out, as_json)


def _emit(out, as_json):
    if as_json:
        return json.dumps(out, ensure_ascii=False, indent=2)
    lines = []
    lines.append("🎯 孙子·战略决策引导")
    lines.append("─" * 32)
    lines.append("· 输入：%s" % out["input"])
    if out.get("red_flag"):
        lines.append("⚠ 红线：%s" % out["message"])
        lines.append("★ 动作：%s" % out["action"])
        return "\n".join(lines)
    lines.append("· 结论：%s" % out["verdict"])
    if out.get("scene"):
        lines.append("· 识别场景：%s" % out["scene"])
        lines.append("· 提示：%s" % out["scene_tip"])
    for b in out.get("frameworks", []):
        lines.append("─" * 32)
        lines.append("▣ 框架：%s（%s）" % (b["name"], b["purpose"]))
        qs = b.get("guide_questions", b.get("steps", []))
        if qs:
            lines.append("  引导问题：")
            for i, q in enumerate(qs, 1):
                lines.append("    %d. %s" % (i, q))
        if b.get("output"):
            lines.append("  → 产出：%s" % b["output"])
    lines.append("─" * 32)
    lines.append("★ 红线：%s" % out.get("redline", "本工具为战略思维引导，非法律/财务/专业咨询；重大经营与投资决策须结合实际并咨询专业顾问。"))
    return "\n".join(lines)


if __name__ == "__main__":
    arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    is_json = "--json" in sys.argv
    if is_json:
        arg = arg.replace("--json", "").strip()
    print(run(arg, as_json=is_json))
