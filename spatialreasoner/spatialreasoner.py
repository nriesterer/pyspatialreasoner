import os
import logging
import queue
import subprocess
import threading


# Term names
TERMS = [
    'square',
    'triangle',
    'circle',
    'line',
    'cross',
    'ell',
    'vee',
    'star',
    'ess',
]

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

                if text == '> Error: The value NIL is not of the expected type ARRAY.':
                    logger.debug('error encountered. popping...')
                    self._send(':POP')

                if text == 'PREMISE  FOLLOWS  VALIDLY  FROM  PREVIOUS  PREMISES.':
                    logger.debug('validity detected.')
                    self.resp_queue.put('true')

                if text == 'PREMISE  IS  INCONSISTENT  WITH  PREVIOUS  PREMISES.':
                    logger.debug('invalidity detected.')
                    self.resp_queue.put('false')

                if text == 'PREMISE  WAS  PREVIOUSLY  POSSIBLY  TRUE.':
                    logger.debug('indeterminate true detected.')
                    self.resp_queue.put('indeterminate-true')

                if text == 'PREMISE  WAS  PREVIOUSLY  POSSIBLY  FALSE.':
                    logger.debug('indeterminate false detected.')
                    self.resp_queue.put('indeterminate-false')

        self.readerstdout = threading.Thread(target=stdout_reader, args=(self.proc,), daemon=True)
        self.readerstdout.start()

        # Create the FASL file if not existent
        lisp_dir = os.path.abspath(os.path.split(os.path.abspath(__file__))[0] + '/lisp')
        lisp_path = os.path.abspath(lisp_dir + '/spatial.lisp')
        fasl_path = os.path.abspath(lisp_dir + '/spatial.dx64fsl')

        if not os.path.isfile(fasl_path):
            self.logger.debug('compiling the lisp code...')
            spatial_reasoner_file = lisp_path.replace('\\', '\\\\')
            self._send('(compile-file "{}")'.format(spatial_reasoner_file))

        # Load spatialreasoner
        logging.debug('loading spatialreasoner fasl...')
        self._send('(load "{}")'.format(fasl_path))

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

    def query(self, problem, expected_no_responses=1):
        self.logger.debug('Querying for problem "%s"', problem)

        # Prepare the command to send
        premises = ''.join(['({})'.format(x) for x in problem])
        cmd = "(interpret '({}))".format(premises)
        self.logger.debug('cmd: "%s"', cmd)

        # Send the command
        self._send(cmd)

        # Wait for the response
        response_list = []
        for _ in range(expected_no_responses):
            resp = self.resp_queue.get()
            if resp == 'false':
                return ['false']
            response_list.append(resp)
        return response_list
