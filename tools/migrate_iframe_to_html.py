"""
Migrate st.iframe() calls in app_unloadv1.7.py:
- calls with height=0  → st.html(..., unsafe_allow_javascript=True)
- calls with height>0  → st.iframe(...) as-is (already valid)
- calls with no height → st.html(..., unsafe_allow_javascript=True)
"""
import re, sys, pathlib

APP = pathlib.Path("app_unloadv1.7.py")
text = APP.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Step 1: Replace  st.iframe(  with  st.html(  globally.
#         We will restore the positive-height ones in Step 3.
# ---------------------------------------------------------------------------
patched = text.replace("st.iframe(", "st.html(")

# ---------------------------------------------------------------------------
# Step 2a: For multi-line calls, replace the "    height=0," line with
#          "    unsafe_allow_javascript=True,"  (preserving indentation).
# ---------------------------------------------------------------------------
patched = re.sub(
    r'(?m)^([ \t]*)height=0,[ \t]*\r?\n',
    r'\1unsafe_allow_javascript=True,\n',
    patched,
)

# Step 2b: For inline calls like  st.html(script, height=0)
patched = patched.replace(", height=0)", ", unsafe_allow_javascript=True)")
patched = patched.replace(", height=0,", ", unsafe_allow_javascript=True,")

# ---------------------------------------------------------------------------
# Step 3: Restore the 3 positive-height visible-render calls back to
#         st.iframe().  These are identified by their height values.
#         Timer html (236), break html (variable), sidebar clock (38).
# ---------------------------------------------------------------------------
# Pattern: st.html(timer_html, height=236)
patched = patched.replace(
    "st.html(timer_html, height=236)",
    "st.iframe(timer_html, height=236)",
)
# Pattern: st.html(break_html, height=break_component_height)
patched = patched.replace(
    "st.html(break_html, height=break_component_height)",
    "st.iframe(break_html, height=break_component_height)",
)
# Sidebar clock block: st.html(  (...), height=38, )
# This is a multi-line block.  The height=38 arg is now GONE (we only stripped
# height=0 lines).  We just need to restore st.iframe for this block.
# Since the sidebar clock call's inner HTML includes a distinctive string, we can
# target it.
patched = re.sub(
    r'(st\.html\(\s*\(\s*"<!doctype html>"[\s\S]*?"</body></html>"\s*\),\s*height=38,)',
    lambda m: m.group(0).replace("st.html(", "st.iframe(", 1),
    patched,
)

# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------
remaining_h0 = len(re.findall(r'height=0', patched))
iframe_count  = len(re.findall(r'\bst\.iframe\(', patched))
html_count    = len(re.findall(r'\bst\.html\(', patched))
remaining_deprecated = len(re.findall(r'components\.v1\.html', patched))

print(f"height=0 remaining:     {remaining_h0}")
print(f"st.iframe() calls:      {iframe_count}")
print(f"st.html() calls:        {html_count}")
print(f"components.v1.html:     {remaining_deprecated}")

APP.write_text(patched, encoding="utf-8")
print("Done. File written.")
