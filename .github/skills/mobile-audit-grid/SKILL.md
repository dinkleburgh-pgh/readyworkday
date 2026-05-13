# Mobile Audit Grid Layout Pattern

## Problem
Streamlit's `st.columns()` layout collapses to single column on mobile viewports (≤980px), making multi-column audit category buttons unusable on phones/tablets.

## Solution
Use a **key-targeted DOM grid script** that:
1. Identifies the audit tiles by their unique `data-key` attributes
2. Forces a stable CSS grid layout independent of Streamlit's column stacking
3. Applies only to the specific audit section (avoids global regressions)

## Implementation Steps

### 1. Render audit tiles with Streamlit columns (standard approach)
```python
col1, col2 = st.columns(2)
with col1:
    st.button("3x10", key="audit_3x10", use_container_width=True)
with col2:
    st.button("3x5", key="audit_3x5", use_container_width=True)
```

### 2. Add key-targeted DOM grid script after rendering
Place this **immediately after** the audit tile section in the HTML injection:

```python
st.markdown(
    """
    <script>
    (function() {
      function force_audit_grid_mobile() {
        const mobile = window.innerWidth <= 980;
        if (!mobile) return;
        
        const auditKeys = ["audit_3x10", "audit_3x5", "audit_4x6", "audit_paper"];
        const gridCols = 2;
        const gap = "8px";
        
        for (const key of auditKeys) {
          const elem = document.querySelector(`[data-testid="stButton"]:has(button[aria-label*="${key}"])`);
          if (elem) {
            elem.style.display = "grid";
            elem.style.gridColumn = "auto";
          }
        }
        
        const parentContainer = document.querySelector('[data-testid="stForm"]')?.parentElement;
        if (parentContainer) {
          parentContainer.style.display = "grid";
          parentContainer.style.gridTemplateColumns = `repeat(${gridCols}, 1fr)`;
          parentContainer.style.gap = gap;
          parentContainer.style.maxWidth = "100%";
        }
      }
      
      force_audit_grid_mobile();
      window.addEventListener("resize", force_audit_grid_mobile);
    })();
    </script>
    """,
    unsafe_allow_html=True,
)
```

### 3. Add full-width button after the grid
```python
st.button("Bulk", key="audit_bulk", use_container_width=True)
```

## Key Principles

✅ **Do** use key-targeted selectors (`data-testid`, aria-labels)  
✅ **Do** apply styles only on mobile (`window.innerWidth <= 980`)  
✅ **Do** use grid-based layout forcing (more stable than flexbox)  
✅ **Do** listen to resize events for responsive changes  

❌ **Don't** use broad CSS selectors that affect unrelated elements  
❌ **Don't** target by element count or nth-child (fragile)  
❌ **Don't** apply globally (causes regressions on other pages)  

## Why This Works

1. **Escapes Streamlit stacking**: DOM script overrides Streamlit's responsive column collapse
2. **Key-targeted**: Only affects audit tiles, not other page elements
3. **Responsive**: Resize listener re-applies on viewport changes
4. **Mobile-first**: Conditional check prevents desktop interference
5. **Precedence**: Inline grid styles override Streamlit's default `flex-direction: column`

## Testing Checklist

- [ ] Audit tiles render in 2x2 grid on mobile (width ≤980px)
- [ ] Bulk button spans full width below grid
- [ ] Desktop layout unaffected (width >980px shows normal Streamlit columns)
- [ ] Resize window → tiles reflow correctly
- [ ] No regressions on other pages (Off, Dirty, Unloaded, etc.)
- [ ] Works across browsers (Chrome, Safari, Firefox)

## Related Patterns

See also:
- `_force_mobile_button_grid()` for general fleet button grid forcing
- `_render_audit_capture_panel()` for full audit workflow implementation
