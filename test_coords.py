"""Quick test to verify DPI-aware coordinate scaling."""
import pyautogui
import mss

# Logical (pyautogui space - where clicks happen)
logical = pyautogui.size()
print(f"pyautogui (logical): {logical.width}x{logical.height}")

# Physical (mss capture space)
with mss.mss() as sct:
    mon = sct.monitors[1]  # primary
    phys_w = mon["width"]
    phys_h = mon["height"]
    print(f"mss (physical): {phys_w}x{phys_h}")

# DPI scale
dpi_x = phys_w / logical.width
dpi_y = phys_h / logical.height
print(f"DPI scale: {dpi_x:.4f}x{dpi_y:.4f} ({dpi_x*100:.0f}%)")

# Simulate what happens when we resize for LLM
max_width = 1280
if phys_w > max_width:
    ratio = max_width / phys_w
    sent_w = max_width
    sent_h = int(phys_h * ratio)
else:
    sent_w, sent_h = phys_w, phys_h

print(f"Image sent to LLM: {sent_w}x{sent_h}")

# Test: LLM gives coords in image space, we need pyautogui space
test_coords = [(640, 450), (100, 100), (1000, 600), (sent_w-1, sent_h-1)]
for llm_x, llm_y in test_coords:
    real_x = int(round(llm_x * (logical.width / sent_w)))
    real_y = int(round(llm_y * (logical.height / sent_h)))
    print(f"  LLM ({llm_x},{llm_y}) -> pyautogui ({real_x},{real_y})")

# Summary
if dpi_x == 1.0 and sent_w == logical.width:
    print("\n=> No scaling needed (DPI=100%, no resize)")
elif dpi_x == 1.0:
    print(f"\n=> Only resize scaling: {sent_w}→{logical.width} ({logical.width/sent_w:.3f}x)")
else:
    print(f"\n=> DPI + resize scaling: sent={sent_w} -> physical={phys_w} -> logical={logical.width}")
