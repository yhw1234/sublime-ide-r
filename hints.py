import sublime
import sublime_plugin
import re
import json
import os


def load_jsonfile(pkg):
    data = None

    jsonFilepath = "/".join(['Packages', 'R-Box', 'packages', '%s.json' % pkg])
    try:
        data = json.loads(sublime.load_resource(jsonFilepath))
    except IOError:
        pass

    if data:
        return data

    jsonFilepath = os.path.join(sublime.packages_path(), "User",
                                'R-Box', 'packages', '%s.json' % pkg)
    if os.path.exists(jsonFilepath):
        with open(jsonFilepath, "r") as f:
            data = json.load(f)

    return data


class RBoxHintsListener(sublime_plugin.EventListener):
    cache = {}
    last_row = 0

    def check(self, view):
        if view.is_scratch() or view.settings().get('is_widget'):
            return False

        sel = view.sel()
        if len(sel) != 1:
            return

        if sel[0].begin() != sel[0].end():
            return

        point = sel[0].end() if len(sel) > 0 else 0
        if not view.score_selector(point, "source.r"):
            return False

        settings = sublime.load_settings('R-Box.sublime-settings')
        return settings.get("show_hints", True)

    def on_modified_async(self, view):
        if not self.check(view):
            return

        vid = view.id()
        if vid not in self.cache:
            return

        point = view.sel()[0].end() if len(view.sel()) > 0 else 0
        contentb = view.substr(sublime.Region(view.line(point).begin(), point))
        m = re.match(r".*?([a-zA-Z0-9._]+)\($", contentb)
        func = m.group(1) if m else None
        if not func:
            return

        if func in self.cache[vid]:
            view.show_popup(
                self.cache[vid][func],
                sublime.COOPERATE_WITH_AUTO_COMPLETE | sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                max_width=600)

    def on_hover(self, view, point, hover_zone):
        if not self.check(view):
            return

        vid = view.id()
        if vid not in self.cache:
            return

        if hover_zone != sublime.HOVER_TEXT:
            return

        word_region = view.word(point)
        if view.substr(word_region.end()) != "(":
            return

        func = view.substr(view.word(point))
        if func in self.cache[vid]:
            view.show_popup(
                self.cache[vid][func],
                sublime.COOPERATE_WITH_AUTO_COMPLETE | sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                location=point,
                max_width=600)

    def loaded_libraries(self, view):
        packages = [
            "base",
            "stats",
            "methods",
            "utils",
            "graphics",
            "grDevices"
        ]
        for s in [view.substr(s) for s in view.find_all("(?:library|require)\(([^)]*?)\)")]:
            m = re.search(r"""\((?:"|')?(.*?)(?:"|')?\)""", s)
            if m:
                packages.append(m.group(1))

        packages = list(set(packages))
        methods = {}
        for pkg in packages:
            j = load_jsonfile(pkg)
            if j:
                methods.update(j.get("methods"))

        results = view.find_all(r"""\b(?:[a-zA-Z0-9._:]*)\s*(?:<-|=)\s*function\s*"""
                                r"""(\((?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^()]|(?1))*\))""")
        for s in results:
            m = re.match(r"^([^ ]+)\s*(?:<-|=)\s*(?:function)\s*(.+)$", view.substr(s))
            if m:
                methods.update({m.group(1): m.group(1)+m.group(2)})

        vid = view.id()
        self.cache[vid] = methods

    def on_post_save_async(self, view):
        if self.check(view):
            self.loaded_libraries(view)

    def on_load_async(self, view):
        if self.check(view):
            self.loaded_libraries(view)

    def on_activated_async(self, view):
        if self.check(view):
            self.loaded_libraries(view)