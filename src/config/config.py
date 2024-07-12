class BuildConfig:
    download_path = ""
    phase_member = ["prep", "build", "configure", "install", "check", "clean"]
    language_for_compilation = {
        "python": "python",
        "ruby": "rubygem",
        "java": "maven",
        "javascript": "nodejs",
        "perl": "perl",
    }
    logfile = "build.log"


configuration = BuildConfig()
