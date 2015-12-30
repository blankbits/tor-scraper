# Copyright 2015 Peter Dymkar Brandt All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""TorScraper is a utility for multi-threaded scraping via the Tor network.

It provides a clean interface for anonymously scraping data from the web
simultaneously through multiple Tor exit nodes. This is useful for maintaining
privacy, circumventing IP blocking and various forms of censorship, and going
beyond what rate limits would otherwise allow.

Example:
    import tor_scraper
    scraper = tor_scraper.TorScraper(
         {'thread_count': 1,
          'socks_port_offset': 9250,
          'control_port_offset': 9350,
          'data_directory': 'tor_data/',
          'tor_cmd': '/Applications/TorBrowser.app/TorBrowser/Tor/tor.real',
          'public_ip_url': 'https://api.ipify.org',})
    scraper.add_scrape('http://www.apache.org/licenses/LICENSE-2.0')
    scraper.run()
"""

import io
import logging
import Queue
import threading

import pycurl
import stem.process

class TorScraper(object):
    """Encapsulates the core functionality of the tor_scraper module.
    """
    def __init__(self, config):
        """TorScraper must be initialized with a config arg similar to that
        shown in the example at the top of this file. The public_ip_url key
        is optional.

        Args:
            config: Determines the behavior of this instance.
        """
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._scrape_queue = Queue.Queue()

    def run(self):
        """Creates an arbitrary number of Tor processes and threads as specified
        in the config, then blocks until all scraping has finished.
        """
        # Start Tor processes.
        tor_processes = []
        for index in range(self._config['thread_count']):
            tor_processes.append(stem.process.launch_tor_with_config(
                tor_cmd=self._config['tor_cmd'],
                config={
                    'SocksPort': str(self._config['socks_port_offset'] + index),
                    'ControlPort': str(self._config['control_port_offset'] +
                                       index),
                    'DataDirectory': (self._config['data_directory'] +
                                      str(index)),
                },
                init_msg_handler=self._tor_init_msg_handler
            ))
            # Log public IP thru Tor.
            if self._config['public_ip_url'] != '':
                self._logger.info('Public IP: ' +
                                  self._query(
                                      self._config['public_ip_url'],
                                      self._config['socks_port_offset'] +
                                      index))

        # Start Tor threads.
        tor_threads = []
        for index in range(self._config['thread_count']):
            tor_thread = threading.Thread(target=self._tor_worker,
                                          args=(index,))
            tor_thread.start()
            tor_threads.append(tor_thread)

        # Wait for Tor threads to finish.
        for tor_thread in tor_threads:
            tor_thread.join()

        # Kill Tor processes.
        for tor_process in tor_processes:
            tor_process.kill()

    def _default_handler(self, url, context, result):
        """Writes result of scrape and other args to the logger.

        Args:
            url: URL which was scraped.
            context: The same context passed to add_scrape(...).
            result: Raw bytes resulting from the scrape.
        """
        self._logger.debug('url: %s', url)
        self._logger.debug('context: %s', context)
        self._logger.debug('result: %s', result)

    def add_scrape(self, url, context=None, handler=None):
        """Push a new scrape task on the queue and optionally set context and
        handler callback to process the result.

        Args:
            url: URL to be scraped.
            context: Arbitrary context associated with this scrape.
            handler: Callback called upon scrape completion. This must have the
                same function signature as _default_handler(...).
        """
        if handler is None:
            handler = self._default_handler

        self._scrape_queue.put({'url': url, 'context': context,
                                'handler': handler})

    def _query(self, url, socks_port):
        """Uses pycurl to fetch a site using the proxy on the socks_port.
        """
        output = io.BytesIO()
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.PROXY, 'localhost')
        curl.setopt(pycurl.PROXYPORT, socks_port)
        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
        curl.setopt(pycurl.WRITEFUNCTION, output.write)

        try:
            curl.perform()
            return output.getvalue()
        except pycurl.error as exc:
            self._logger.error('Unable to reach %s (%s)', url, exc)
            return None

    def _tor_init_msg_handler(self, line):
        """Handles messages output by stem and writes them to the logger.
        """
        if 'Bootstrapped ' in line:
            self._logger.info(line.rsplit('[notice] ', 1)[1])

    def _tor_worker(self, index):
        """Function for worker thread to execute scrape tasks from the queue.
        Loops until the queue is empty, then returns.
        """
        self._logger.info('Starting _tor_worker:' + str(index))
        while True:
            try:
                scrape = self._scrape_queue.get(False)
            except Queue.Empty:
                break
            else:
                self._logger.debug('Scraping _tor_worker:' + str(index) +
                                   ' url:' + scrape['url'])
                result = self._query(scrape['url'],
                                     self._config['socks_port_offset'] + index)
                scrape['handler'](scrape['url'], scrape['context'], result)

                # Tell queue task is complete.
                self._scrape_queue.task_done()
