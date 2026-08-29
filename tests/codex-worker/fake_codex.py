#!/usr/bin/env python3
"""Deterministic JSONL stand-in for ``codex app-server`` integration tests."""
import argparse
import json
import os
import socket
import sys
import threading
import time
import traceback
from urllib.parse import urlsplit
from pathlib import Path


class FakeCodex:
    def __init__(self, mode, delay, scenario=None, capture_path=None):
        self.mode = mode
        self.scenario = scenario or {}
        self.delay = self.scenario.get("delay", delay)
        self.capture_path = Path(capture_path) if capture_path else None
        self.initialized = False
        self.thread_id = "thr-fake"
        self.thread_number = 0
        self.thread_cwds = {}
        self.turn_number = 0
        self.active_turn = None
        self.active_turns = {}
        self.write_lock = threading.Lock()
        self.capture_lock = threading.Lock()
        self.capture_sequence = 0
        self.turn_barrier = threading.Event()
        self.approval_request_id = 9001
        self.goal = None
        self.turn_pages = {
            None: ([{"id": "turn-new", "status": "completed", "items": []}], "cursor-old"),
            "cursor-old": ([{"id": "turn-old", "status": "completed", "items": []}], None),
        }
        self.turn_list_requests = []
        self.inventory_reads = 0
        self.ambiguous_inventory_active = False
        self.websocket = None

    def option(self, key, default=None):
        return self.scenario.get(key, default)

    def capture(self, message):
        """Append received JSON-RPC data without making the fake's behavior implicit."""
        self._write_receipt({"kind": "request", "method": message.get("method"),
                             "params": message.get("params", {}), "id": message.get("id")})

    def receipt(self, kind, **values):
        values["kind"] = kind
        self._write_receipt(values)

    def _write_receipt(self, payload):
        if self.capture_path is None:
            return
        with self.capture_lock:
            self.capture_sequence += 1
            row = {"seq": self.capture_sequence, "at": time.monotonic(), "pid": os.getpid()}
            row.update(payload)
            fd = os.open(str(self.capture_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, (json.dumps(row, separators=(",", ":")) + "\n").encode("utf-8"))
            finally:
                os.close(fd)

    def send(self, message):
        encoded = json.dumps(message, separators=(",", ":"))
        with self.write_lock:
            if self.websocket is not None:
                self.websocket.send(encoded)
            else:
                sys.stdout.write(encoded + "\n")
                sys.stdout.flush()

    def response(self, request_id, result):
        self.send({"id": request_id, "result": result})

    def complete_later(self, thread_id, turn_id, prompt):
        barrier_count = self.option("turn_barrier")
        if type(barrier_count) is int and barrier_count > 0:
            if not self.turn_barrier.wait(timeout=5.0):
                self.receipt("barrier_timeout", prompt=prompt, thread_id=thread_id,
                             turn_id=turn_id, expected=barrier_count)
                return
        delays = self.scenario.get("turn_delays", {})
        time.sleep(delays.get(prompt, self.delay) if isinstance(delays, dict) else self.delay)
        if self.active_turns.get(thread_id) != turn_id:
            return
        outputs = self.option("turn_outputs", {})
        output = outputs.get(prompt, "done:%s" % prompt) if isinstance(outputs, dict) else "done:%s" % prompt
        contains_outputs = self.option("turn_output_contains", {})
        if isinstance(contains_outputs, dict):
            output = next((value for marker, value in contains_outputs.items()
                           if marker in prompt), output)
        phases = self.option("turn_phases", {})
        phase = phases.get(prompt) if isinstance(phases, dict) else None
        if self.option("no_agent_messages", False):
            messages = []
        elif isinstance(output, list):
            messages = output
        else:
            messages = [output]
        for index, text in enumerate(messages):
            item = {"id": "item-%s-%d" % (turn_id, index), "type": "agentMessage", "text": text,
                    "phase": phase if index == len(messages) - 1 else "final_answer"}
            if self.option("usage", True): item["tokenUsage"] = {"totalTokens": 7 + index}
            self.send({"method": "item/completed", "params": {"threadId": thread_id,
                       "turnId": turn_id, "item": item}})
        duration = self.option("command_duration_ms")
        if type(duration) is int:
            self.send({"method": "item/completed", "params": {"threadId": thread_id, "turnId": turn_id,
                       "item": {"id": "command-%s" % turn_id, "type": "commandExecution", "durationMs": duration}}})
        statuses = self.option("turn_status_contains", {})
        status = next((value for marker, value in statuses.items() if marker in prompt),
                      "completed") if isinstance(statuses, dict) else "completed"
        self.send({
            "method": "turn/completed",
            "params": {
                "threadId": thread_id,
                "turn": {"id": turn_id, "status": status, "items": []},
            },
        })
        self.active_turns.pop(thread_id, None)
        self.receipt("completion", prompt=prompt, thread_id=thread_id, turn_id=turn_id, output=output)
        if self.active_turn == turn_id:
            self.active_turn = None

    def approval_method(self):
        return {
            "approval-command": "item/commandExecution/requestApproval",
            "approval-file": "item/fileChange/requestApproval",
            "approval-user": "item/tool/requestUserInput",
            "approval-permissions": "item/permissions/requestApproval",
        }.get(self.mode)

    def handle_turn_start(self, message):
        self.turn_number += 1
        barrier_count = self.option("turn_barrier")
        if type(barrier_count) is int and self.turn_number >= barrier_count:
            self.turn_barrier.set()
        turn_id = "turn-%d" % self.turn_number
        thread_id = message["params"]["threadId"]
        inputs = message["params"].get("input", [])
        prompt = inputs[0].get("text", "") if inputs and isinstance(inputs[0], dict) else ""
        notified_id = "turn-notified" if self.mode == "mismatch-before-response" else turn_id
        self.active_turn = notified_id
        self.active_turns[thread_id] = notified_id
        started = {
            "method": "turn/started",
            "params": {
                "threadId": thread_id,
                "turn": {"id": notified_id, "status": "inProgress", "items": []},
            },
        }
        if self.mode in ("complete-before-response", "mismatch-before-response"):
            self.send(started)
            self.send({
                "method": "turn/completed",
                "params": {
                    "threadId": thread_id,
                    "turn": {"id": notified_id, "status": "completed", "items": []},
                },
            })
            self.active_turns.pop(thread_id, None)
            self.active_turn = None
            self.response(message["id"], {"turn": {"id": turn_id, "status": "inProgress"}})
            return

        self.response(message["id"], {"turn": {"id": turn_id, "status": "inProgress"}})
        self.send(started)
        approval_method = self.approval_method()
        if approval_method:
            params = {
                "threadId": thread_id,
                "turnId": turn_id,
                "itemId": "approval-item",
                "reason": "SECRET prompt content",
                "command": "echo SECRET",
                "questions": [{"id": "secret-question", "question": "SECRET?"}],
                "permissions": {"network": {"enabled": True}},
            }
            self.send({"id": self.approval_request_id, "method": approval_method, "params": params})
        else:
            threading.Thread(target=self.complete_later,
                             args=(thread_id, turn_id, prompt), daemon=True).start()

    def handle(self, message):
        self.capture(message)
        method = message.get("method")
        request_id = message.get("id")
        malformed = self.option("malformed", {})
        if isinstance(malformed, dict) and method in malformed:
            value = malformed[method]
            if value == "invalid_json":
                sys.stdout.write("{not-json\n"); sys.stdout.flush(); return
            if value == "non_object":
                self.send([]); return
            if isinstance(value, dict):
                self.response(request_id, value); return
        if method == "initialize":
            self.initialized = True
            self.response(request_id, {"userAgent": "fake-codex"})
        elif method == "initialized":
            return
        elif not self.initialized:
            self.send({"id": request_id, "error": {"code": -32000, "message": "Not initialized"}})
        elif method == "model/list":
            if self.mode == "malformed":
                with self.write_lock:
                    sys.stdout.write("{not-json\n")
                    sys.stdout.flush()
            elif self.mode == "exit":
                raise SystemExit(7)
            else:
                self.response(request_id, {"data": self.option("models", [
                    {"id": "fake-model-a", "supportedReasoningEfforts": [{"reasoningEffort": "medium"}]},
                    {"id": "fake-model-b", "supportedReasoningEfforts": [{"reasoningEffort": "high"}]},
                ])})
        elif method == "thread/start":
            self.thread_number += 1
            self.thread_id = "thr-fake" if self.thread_number == 1 else "thr-fake-%d" % self.thread_number
            self.thread_cwds[self.thread_id] = message["params"]["cwd"]
            self.response(request_id, {"thread": {"id": self.thread_id, "cwd": message["params"]["cwd"]}})
        elif method == "thread/resume":
            self.thread_id = message["params"]["threadId"]
            self.response(request_id, {"thread": {"id": self.thread_id,
                                                    "cwd": self.thread_cwds.get(
                                                        self.thread_id,
                                                        os.environ.get(
                                                            "FAKE_CODEX_RESUME_CWD",
                                                            os.getcwd()))}})
        elif method == "thread/list":
            self.inventory_reads += 1
            data = []
            for thread_id in sorted(self.thread_cwds):
                status = ({"type": "active", "activeFlags": []}
                          if thread_id in self.active_turns else {"type": "idle"})
                data.append({"id": thread_id, "status": status})
            ambiguous = self.option("ambiguous_inventory_thread")
            read_limit = self.option("ambiguous_inventory_reads", 0)
            self.ambiguous_inventory_active = (
                isinstance(ambiguous, str) and ambiguous
                and type(read_limit) is int and self.inventory_reads <= read_limit)
            if self.ambiguous_inventory_active:
                data.append({"id": ambiguous,
                             "status": {"type": "active", "activeFlags": []}})
            self.response(request_id, {
                "data": data, "nextCursor": None, "backwardsCursor": None,
            })
        elif method == "thread/read":
            thread_id = message["params"]["threadId"]
            if (self.ambiguous_inventory_active
                    and thread_id == self.option("ambiguous_inventory_thread")):
                self.response(request_id, {"thread": {
                    "id": thread_id, "status": {"type": "active", "activeFlags": []},
                    "turns": [],
                }})
                return
            turns = []
            if thread_id in self.active_turns:
                turns.append({"id": self.active_turns[thread_id],
                              "status": "inProgress", "items": []})
            pages = self.option("history_pages")
            if isinstance(pages, dict):
                for page in pages.values():
                    if isinstance(page, dict) and isinstance(page.get("turns"), list):
                        turns.extend(page["turns"])
            has_active = (thread_id in self.active_turns or any(
                isinstance(turn, dict) and turn.get("status") in ("inProgress", "in_progress")
                for turn in turns))
            status = ({"type": "active", "activeFlags": []}
                      if has_active else {"type": "idle"})
            self.response(request_id, {"thread": {
                "id": thread_id, "status": status, "turns": turns,
            }})
        elif method == "turn/start":
            self.thread_id = message["params"]["threadId"]
            self.handle_turn_start(message)
        elif method == "thread/goal/set":
            if self.option("goal_set_failure", False):
                self.send({"id": request_id, "error": {"code": -32001, "message": "goal rejected"}}); return
            params = message["params"]
            self.goal = {"threadId": params["threadId"], "objective": params.get("objective", "goal"),
                         "status": params.get("status", "active"), "tokenBudget": params.get("tokenBudget"),
                         "tokensUsed": 0, "timeUsedSeconds": 0, "createdAt": 1767225600,
                         "updatedAt": 1767225600}
            self.response(request_id, {"goal": self.goal})
        elif method == "thread/goal/get":
            self.response(request_id, {"goal": None if self.option("goal_absent", False) else self.goal})
        elif method == "thread/turns/list":
            params = message["params"]
            self.turn_list_requests.append({"threadId": params.get("threadId"), "cursor": params.get("cursor"), "limit": params.get("limit")})
            pages = self.option("history_pages")
            if isinstance(pages, dict):
                page = pages.get(str(params.get("cursor")), pages.get("null", {"turns": [], "nextCursor": None}))
                turns, cursor = page.get("turns", []), page.get("nextCursor")
            else:
                turns, cursor = self.turn_pages.get(params.get("cursor"), ([], None))
            self.response(request_id, {
                "data": turns, "nextCursor": cursor, "backwardsCursor": "newer",
            })
        elif method == "account/rateLimits/read":
            if self.option("limits_unavailable", False):
                self.send({"id": request_id, "error": {"code": -32601, "message": "unsupported"}})
            else:
                self.response(request_id, {"rateLimits": self.option("limits", {"primary": {"usedPercent": 1}})})
        elif method == "turn/steer":
            self.response(request_id, {"turnId": message["params"]["expectedTurnId"]})
        elif method == "turn/interrupt":
            turn_id = message["params"]["turnId"]
            thread_id = message["params"]["threadId"]
            self.response(request_id, {})
            if self.active_turns.get(thread_id) == turn_id:
                self.send({
                    "method": "turn/completed",
                    "params": {
                        "threadId": thread_id,
                        "turn": {"id": turn_id, "status": "interrupted", "items": []},
                    },
                })
                self.active_turns.pop(thread_id, None)
                self.active_turn = None
        elif request_id == self.approval_request_id and method is None:
            decision = message.get("result", {})
            self.send({
                "method": "item/completed",
                "params": {
                    "threadId": self.thread_id,
                    "turnId": self.active_turn,
                    "item": {"id": "approval-item", "type": "approvalResult", "decision": decision},
                },
            })
            self.send({
                "method": "turn/completed",
                "params": {
                    "threadId": self.thread_id,
                    "turn": {"id": self.active_turn, "status": "completed", "items": []},
                },
            })
            self.active_turn = None
        else:
            self.send({"id": request_id, "error": {"code": -32601, "message": "unknown method"}})

    def run(self):
        for line in sys.stdin:
            if not line.strip():
                continue
            self.handle(json.loads(line))

    def run_websocket(self, listener):
        from websockets.sync.server import serve

        if listener.startswith("unix://"):
            socket_path = listener[len("unix://"):]
            listening = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listening.bind(socket_path)
            os.chmod(socket_path, 0o600)
            listening.listen()
            with serve(self._websocket_handler, sock=listening, unix=True) as server:
                server.serve_forever()
            return
        parsed = urlsplit(listener)
        if parsed.scheme != "ws" or parsed.hostname is None or parsed.port is None:
            raise ValueError("fake listener must be a ws:// host:port URL")

        with serve(self._websocket_handler, parsed.hostname, parsed.port) as server:
            server.serve_forever()

    def _websocket_handler(self, websocket):
        self.websocket = websocket
        try:
            for message in websocket:
                self.handle(json.loads(message))
        finally:
            self.websocket = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_server", nargs="?", choices=("app-server",))
    parser.add_argument("--listen")
    parser.add_argument("--mode", default="normal")
    parser.add_argument("--delay", type=float, default=0.03)
    parser.add_argument("--scenario")
    parser.add_argument("--capture")
    args = parser.parse_args()
    scenario_path = args.scenario or os.environ.get("FAKE_CODEX_SCENARIO")
    scenario = {}
    if scenario_path:
        scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
        if not isinstance(scenario, dict):
            raise ValueError("scenario must be a JSON object")
    fake = FakeCodex(args.mode, args.delay, scenario,
                     args.capture or os.environ.get("FAKE_CODEX_CAPTURE"))
    if args.listen:
        fake.run_websocket(args.listen)
    else:
        fake.run()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        error_path = os.environ.get("FAKE_CODEX_ERROR")
        if error_path:
            Path(error_path).write_text(traceback.format_exc(), encoding="utf-8")
        raise
