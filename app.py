import importlib.util
import os


def _load_fish_delivery_app():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(root_dir, "artifacts", "fish-delivery", "app.py")
    spec = importlib.util.spec_from_file_location("fish_delivery_app", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_fish_delivery = _load_fish_delivery_app()

root_dir = os.path.dirname(os.path.abspath(__file__))
root_templates = os.path.join(root_dir, "templates")
root_static = os.path.join(root_dir, "static")

if os.path.isdir(root_templates):
    _fish_delivery.app.template_folder = root_templates
    try:
        _fish_delivery.app.jinja_loader.searchpath = [root_templates]
    except Exception:
        pass

if os.path.isdir(root_static):
    _fish_delivery.app.static_folder = root_static

app = _fish_delivery.app

if __name__ == "__main__":
    if hasattr(_fish_delivery, "init_db"):
        _fish_delivery.init_db()
    app.run(host="0.0.0.0")
