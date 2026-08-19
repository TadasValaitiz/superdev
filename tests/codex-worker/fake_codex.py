#!/usr/bin/env python3
"""Deterministic JSONL stand-in for ``codex app-server`` integration tests."""
import argparse
import json
import os
import sys
import threading
import time


class FakeCodex:
    def __init__(self, mode, delay):
        self.mode = mode
        self.delay = delay
        self.initialized = False
        self.thread_id = "thr-fake"
        self.thread_number = 0
        self.thread_cwds = {}
        self.turn_number = 0
        self.active_turn = None
        self.active_turns = {}
        self.write_lock = threading.Lock()
        self.approval_request_id = 9001
        self.goal = None
        self.turn_pages = {
            None: ([{"id": "turn-new", "status": "completed", "items": []}], "cursor-old"),
            "cursor-old": ([{"id": "turn-old", "status": "completed", "items": []}], None),
        }
        self.turn_list_requests = []

    def send(self, message):
        encoded = json.dumps(message, separators=(",", ":")) + "\n"
        with self.write_lock:
            sys.stdout.write(encoded)
            sys.stdout.flush()

    def response(self, request_id, result):
        self.send({"id": request_id, "result": result})

    def complete_later(self, thread_id, turn_id, prompt):
        time.sleep(self.delay)
        if self.active_turns.get(thread_id) != turn_id:
            return
        self.send({
            "method": "item/completed",
            "params": {
                "threadId": thread_id,
                "turnId": turn_id,
                "item": {"id": "item-%s" % turn_id, "type": "agentMessage",
                         "text": "done:%s" % prompt, "phase": None,
                         "tokenUsage": {"totalTokens": 7}},
            },
        })
        self.send({
            "method": "turn/completed",
            "params": {
                "threadId": thread_id,
                "turn": {"id": turn_id, "status": "completed", "items": []},
            },
        })
        self.active_turns.pop(thread_id, None)
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
        method = message.get("method")
        request_id = message.get("id")
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
                self.response(request_id, {"data": [
                    {"id": "fake-model-a", "supportedReasoningEfforts": [{"reasoningEffort": "medium"}]},
                    {"id": "fake-model-b", "supportedReasoningEfforts": [{"reasoningEffort": "high"}]},
                ]})
        elif method == "thread/start":
            self.thread_number += 1
            self.thread_id = "thr-fake" if self.thread_number == 1 else "thr-fake-%d" % self.thread_number
            self.thread_cwds[self.thread_id] = message["params"]["cwd"]
            self.response(request_id, {"thread": {"id": self.thread_id, "cwd": message["params"]["cwd"]}})
        elif method == "thread/resume":
            self.thread_id = message["params"]["threadId"]
            self.response(request_id, {"thread": {"id": self.thread_id,
                                                    "cwd": self.thread_cwds.get(self.thread_id, os.getcwd())}})
        elif method == "turn/start":
            self.thread_id = message["params"]["threadId"]
            self.handle_turn_start(message)
        elif method == "thread/goal/set":
            params = message["params"]
            self.goal = {"threadId": params["threadId"], "objective": params.get("objective", "goal"),
                         "status": params.get("status", "active"), "tokenBudget": params.get("tokenBudget"),
                         "tokensUsed": 0, "timeUsedSeconds": 0, "createdAt": "2026-01-01T00:00:00Z",
                         "updatedAt": "2026-01-01T00:00:00Z"}
            self.response(request_id, {"goal": self.goal})
        elif method == "thread/goal/get":
            self.response(request_id, {"goal": self.goal})
        elif method == "thread/turns/list":
            params = message["params"]
            self.turn_list_requests.append({"threadId": params.get("threadId"), "cursor": params.get("cursor"), "limit": params.get("limit")})
            turns, cursor = self.turn_pages.get(params.get("cursor"), ([], None))
            self.response(request_id, {"turns": turns, "nextCursor": cursor})
        elif method == "account/rateLimits/read":
            self.response(request_id, {"rateLimits": {"primary": {"usedPercent": 1}}})
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="normal")
    parser.add_argument("--delay", type=float, default=0.03)
    args = parser.parse_args()
    FakeCodex(args.mode, args.delay).run()


if __name__ == "__main__":
    main()
