import os
import logging
import queue
import subprocess
import threading

class SpatialReasoner():
    def __init__(self, ccl):
        self.logger = logging.getLogger(__name__)

        # Start the LISP process
        self.proc = subprocess.Popen(
            [ccl.exec_path()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # Instantiate the result queue
        self.resp_queue = queue.Queue()

        # Register the readers
        def stdout_reader(proc):
            # Setup thread logger
            logger = logging.getLogger(__name__ + '-reader')
            logger.debug('Starting reader...')

            while True:
                # Read text
                text = proc.stdout.readline().decode('ascii').strip()
                logger.debug('spatialreasoner:%s', text)

                if 'TERMINATE' in text:
                    logger.debug('termination handling initiated...')
                    break

        self.readerstdout = threading.Thread(target=stdout_reader, args=(self.proc,), daemon=True)
        self.readerstdout.start()

        # Load spatialreasoner
        spatial_reasoner_file = os.path.abspath(os.path.split(os.path.abspath(__file__))[0] + '/lisp/spatial.lisp')
        spatial_reasoner_file = spatial_reasoner_file.replace('\\', '\\\\')
        self._send('(compile-file "{}")'.format(spatial_reasoner_file))

    def _send(self, cmd):
        """ Send a command to the Clozure Common LISP subprocess.

        Parameters
        ----------
        cmd : str
            Command to send.

        """

        # Normalize the command
        cmd = cmd.strip()

        self.logger.debug('Send:%s', cmd)
        self.proc.stdin.write('{}\n'.format(cmd).encode('ascii'))
        self.proc.stdin.flush()

    def terminate(self):
        """ Terminate mReasoner and its parent instance of Clozure Common LISP.

        """

        # Shutdown the threads
        self._send('(prin1 "TERMINATE")')
        self.logger.debug('Waiting for stdout...')
        self.readerstdout.join()

        # Terminate Clozure
        self._send('(quit)')

