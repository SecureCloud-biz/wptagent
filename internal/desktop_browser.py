# Copyright 2017 Google Inc. All rights reserved.
# Use of this source code is governed by the Apache 2.0 license that can be
# found in the LICENSE file.
"""Base class support for desktop browsers"""
import logging
import os
import shutil
import subprocess
import time
import constants
import monotonic

class DesktopBrowser(object):
    """Desktop Browser base"""
    def __init__(self, path, job):
        self.path = path
        self.proc = None
        self.job = job

    def prepare(self, task):
        """Prepare the profile/OS for the browser"""
        try:
            from .os_util import kill_all
            from .os_util import flush_dns
            logging.debug("Preparing browser")
            kill_all(os.path.basename(self.path), True)
            flush_dns()
            if 'profile' in task:
                if not task['cached'] and os.path.isdir(task['profile']):
                    logging.debug("Clearing profile %s", task['profile'])
                    shutil.rmtree(task['profile'])
                if not os.path.isdir(task['profile']):
                    os.makedirs(task['profile'])
        except BaseException as err:
            logging.critical("Exception preparing Browser: %s", err.__str__())

    def launch_browser(self, command_line):
        """Launch the browser and keep track of the process"""
        logging.debug(command_line)
        self.proc = subprocess.Popen(command_line, shell=True)

    def stop(self):
        """Terminate the browser (gently at first but forced if needed)"""
        from .os_util import kill_all
        logging.debug("Stopping browser")
        if self.proc:
            kill_all(os.path.basename(self.path), False)
            self.proc.terminate()
            self.proc.kill()
            self.proc = None

    def wait_for_idle(self):
        """Wait for no more than 20% of a single core used for 500ms"""
        import psutil
        logging.debug("Waiting for Idle...")
        cpu_count = psutil.cpu_count()
        if cpu_count > 0:
            target_pct = 20. / float(cpu_count)
            idle_start = None
            end_time = monotonic.monotonic() + constants.START_BROWSER_TIME_LIMIT
            idle = False
            while not idle and monotonic.monotonic() < end_time:
                check_start = monotonic.monotonic()
                pct = psutil.cpu_percent(interval=0.1)
                if pct <= target_pct:
                    if idle_start is None:
                        idle_start = check_start
                    if monotonic.monotonic() - idle_start > 0.5:
                        idle = True
                else:
                    idle_start = None

    def clear_profile(self, task):
        """Delete the browser profile directory"""
        if os.path.isdir(task['profile']):
            end_time = monotonic.monotonic() + 30
            while monotonic.monotonic() < end_time:
                shutil.rmtree(task['profile'])
                if os.path.isdir(task['profile']):
                    time.sleep(0.1)
                else:
                    break