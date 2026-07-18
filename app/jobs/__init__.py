"""Background jobs that run as their own long-lived processes.

Like the bots, each job is a standalone service (its own container / systemd
unit) so it can be scaled and restarted independently of the API.
"""
