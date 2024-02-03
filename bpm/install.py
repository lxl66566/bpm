import lastversion as lv
from lastversion.utils import extract_file

a: list[str] = lv.latest(repo="eza-community/eza", output_format="assets", pre_ok=True)
print(a)

extract_file(a[0])
