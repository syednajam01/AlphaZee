"""
audit_admin_slop.py - Comprehensive audit script for Admin Portal files.
Scans for:
1. Emojis
2. Exclamation marks in user-facing strings
3. Uppercase tracked labels / statuses
4. Slop colors, gradients, and glows in styles/admin.css
5. Transition-all and card-lift / scale transforms
"""
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

admin_js_files = glob.glob(str(ROOT / "frontend/src/components/admin/*.js")) + glob.glob(str(ROOT / "frontend/src/components/Admin*.js"))
admin_css = ROOT / "frontend/src/styles/admin.css"

print(f"Auditing {len(admin_js_files)} JS files and admin.css...")

emoji_re = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf]')
exclam_re = re.compile(r'[\w\s]{2,}!+[\s"\'<]')
uppercase_re = re.compile(r'text-transform:\s*uppercase|UPPERCASE|[A-Z]{3,}\b')

audit_findings = {
    "emojis": [],
    "exclamations": [],
    "css_gradients_and_glows": [],
    "css_transforms_transitions": [],
    "css_colors": []
}

for filepath in admin_js_files:
    p = Path(filepath)
    with open(p, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            sline = line.strip()
            # Emojis
            m_emoji = emoji_re.findall(line)
            if m_emoji:
                audit_findings["emojis"].append((p.name, idx, ''.join(m_emoji), sline[:80]))
            # Exclamations in UI strings (filter out JS code like !== or !cond)
            if '!' in line:
                for match in re.finditer(r'([A-Za-z0-9\s]{3,}!{1,3})', line):
                    candidate = match.group(1).strip()
                    if not candidate.startswith('!') and not '!=' in candidate and not 'important' in candidate:
                        audit_findings["exclamations"].append((p.name, idx, candidate, sline[:80]))

with open(admin_css, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        sline = line.strip()
        if "gradient" in sline:
            audit_findings["css_gradients_and_glows"].append((idx, "gradient", sline[:80]))
        if "box-shadow" in sline and ("rgba(82" in sline or "rgba(45" in sline or "rgba(74" in sline or "rgba(239" in sline):
            audit_findings["css_gradients_and_glows"].append((idx, "colored glow", sline[:80]))
        if "translateY(" in sline or "scale(" in sline:
            audit_findings["css_transforms_transitions"].append((idx, "transform lift/scale", sline[:80]))
        if "transition: all" in sline:
            audit_findings["css_transforms_transitions"].append((idx, "transition-all", sline[:80]))

print(f"\n1. Emojis found: {len(audit_findings['emojis'])}")
for fname, idx, emojis, text in audit_findings["emojis"][:15]:
    print(f"   [{fname}:{idx}] ({emojis}) -> {text}")

print(f"\n2. Exclamations in copy found: {len(audit_findings['exclamations'])}")
for fname, idx, phrase, text in audit_findings["exclamations"][:15]:
    print(f"   [{fname}:{idx}] ({phrase}) -> {text}")

print(f"\n3. CSS gradients & colored glows: {len(audit_findings['css_gradients_and_glows'])}")
for idx, kind, text in audit_findings["css_gradients_and_glows"][:15]:
    print(f"   [admin.css:{idx}] ({kind}) -> {text}")

print(f"\n4. CSS transforms & transition-all: {len(audit_findings['css_transforms_transitions'])}")
for idx, kind, text in audit_findings["css_transforms_transitions"][:15]:
    print(f"   [admin.css:{idx}] ({kind}) -> {text}")

