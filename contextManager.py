import json, os, time
from pathlib import Path

class ProjectContext:
    def __init__(self, project_name="default_project"):
        self.project_name = project_name
        self.created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.last_updated = self.created_at
        self.commands = []
        self.files = {}
        self.active_agent = None
        self.last_output = ""
        self.handoffs = []
        self.notes = []

        # Path to persist context
        self.path = Path(f"./context/{self.project_name}.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add_command(self, cmd):
        self.commands.append(cmd)
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    def add_file(self, file_path, content):
        self.files[file_path] = content
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    def add_output(self, output):
        self.last_output = output
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    def add_handoff(self, agent_from, agent_to, reason):
        self.handoffs.append({
            "from": agent_from,
            "to": agent_to,
            "reason": reason,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def add_note(self, note):
        self.notes.append({
            "note": note,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def to_dict(self):
        return {
            "project_name": self.project_name,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "commands": self.commands,
            "files": self.files,
            "handoffs": self.handoffs,
            "notes": self.notes,
            "last_output": self.last_output
        }

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, project_name):
        path = Path(f"./context/{project_name}.json")
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            obj = cls(project_name)
            obj.__dict__.update(data)
            return obj
        return cls(project_name)
