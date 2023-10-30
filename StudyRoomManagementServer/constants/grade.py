class LookupDict(dict):
    """Dictionary lookup object."""

    def __init__(self, name=None):
        self.name = name
        super(LookupDict, self).__init__()

    def __repr__(self):
        return "<lookup '%s'>" % (self.name)

    def __getitem__(self, key):
        # We allow fall-through here, so values default to None
        return self.__dict__.get(str(key), None)

    def get(self, key, default=None):
        return self.__dict__.get(str(key), default)


_grade = {
    0: (
        "회원",
        "normal",
    ),
    10: (
        "원장",
        "vip",
    ),
    15: (
        "플린",
        "manager",
    ),
    20: (
        "관리",
        "admin",
    ),
    -10: (
        "경고",
        "warning",
    ),
    -20: (
        "차단",
        "enemy",
    ),
}

grades = LookupDict(name="grades")


def _init():
    for code, titles in _grade.items():
        setattr(grades, str(code), titles[0])
        for title in titles:
            setattr(grades, title, code)
            if not title.startswith(("\\", "/")):
                setattr(grades, title.upper(), code)

    def doc(code):
        names = ", ".join("``%s``" % n for n in _grade[code])
        return "* %d: %s" % (code, names)

    global __doc__
    __doc__ = (
        __doc__ + "\n" + "\n".join(doc(code) for code in sorted(_grade))
        if __doc__ is not None
        else None
    )


_init()
