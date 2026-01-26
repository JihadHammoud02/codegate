import importlib.metadata

pkg_map = importlib.metadata.distributions()
for i in pkg_map:
    for key, val in i.metadata.items():
        print(f"{val} -> {i.metadata['Name']}")
