#!/usr/bin/env python3
"""Check admin.html for Vue.ref issues"""
import re

with open('/mnt/d/OpenClawData/workspace/Projects/EMA/ui/admin.html') as f:
    content = f.read()
    lines = content.split('\n')

# 1. Find all Vue.ref() declarations
ref_vars = {}
for i, line in enumerate(lines, 1):
    m = re.findall(r'const\s+(\w+)\s*=\s*Vue\.ref\(', line)
    for v in m:
        ref_vars[v] = i

print(f"=== Vue.ref() declarations: {len(ref_vars)} ===")

# 2. Check for missing .value in template section
# Template starts after <div id="app">
template_start = None
for i, line in enumerate(lines, 1):
    if '<div id="app">' in line:
        template_start = i
        break

if template_start:
    print(f"\nTemplate starts at line {template_start}")
    template_lines = lines[template_start-1:]
    
    # Check: in template, ref vars should use .value
    issues = []
    for v, decl_line in ref_vars.items():
        # Check template usage
        for i, line in enumerate(template_lines, template_start):
            if v in line and '.value' not in line and 'Vue.ref' not in line:
                # Flag potential issue
                if '{{' in line or 'v-' in line or ':' in line:
                    issues.append((i, v, line.strip()[:100]))
    
    if issues:
        print(f"\n=== Potential missing .value in template ({len(issues)} issues) ===")
        for line_no, var, text in issues:
            print(f"  Line {line_no} [{var}]: {text}")
    else:
        print("\n=== No obvious missing .value issues in template ===")

# 3. Check setup() return - are all used functions returned?
print("\n=== Checking setup() return ===")
setup_start = None
setup_end = None
brace_depth = 0
for i, line in enumerate(lines, 1):
    if 'setup()' in line and '{' in line:
        setup_start = i
    if setup_start and 'return {' in line:
        # Find the closing }
        for j in range(i, len(lines)):
            if lines[j].strip() == '};' or (lines[j].strip().startswith('}') and 'return' not in lines[j]):
                setup_end = j + 1
                break
        break

if setup_start and setup_end:
    print(f"setup() body: lines {setup_start}-{setup_end}")
    
    # Functions defined inside setup
    setup_funcs = []
    for i in range(setup_start-1, setup_end):
        m = re.match(r'\s*async function (\w+)\(', lines[i])
        if not m:
            m = re.match(r'\s*function (\w+)\(', lines[i])
        if m:
            setup_funcs.append((m.group(1), i+1))
    
    print(f"Functions inside setup(): {[f[0] for f in setup_funcs]}")
    
    # Check return statement
    return_line = None
    for i in range(setup_start-1, setup_end):
        if 'return {' in lines[i]:
            return_line = i + 1
            # Collect all vars in return
            ret_vars = []
            for j in range(i, min(i+40, setup_end)):
                m = re.findall(r'(\w+)', lines[j])
                ret_vars.extend(m)
                if '};' in lines[j] or lines[j].strip() == '};':
                    break
            print(f"Return statement at line {return_line}")
            print(f"Returned vars: {[v for v in ret_vars if v not in ('return','let','const','var','async','function')]}")
            break

# 4. Check for functions defined OUTSIDE setup() that are used in template
print("\n=== Functions defined outside setup() ===")
outside_funcs = []
in_setup = False
for i, line in enumerate(lines, 1):
    if 'setup()' in line and '{' in line:
        in_setup = True
    if in_setup and 'return {' in line:
        in_setup = False
        continue
    if not in_setup:
        m = re.match(r'\s*(?:async )?function (\w+)\(', line)
        if m:
            outside_funcs.append((m.group(1), i))

if outside_funcs:
    print(f"Functions outside setup(): {[f[0] for f in outside_funcs]}")
    print("These won't be accessible in Vue templates!")
else:
    print("No functions defined outside setup()")

print("\n=== Done ===")