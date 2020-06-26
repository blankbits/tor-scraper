# TorScraper
TorScraper is a utility for multi-threaded scraping via the Tor network.

It provides a clean interface for anonymously scraping data from the web simultaneously through multiple Tor exit nodes. This is useful for maintaining privacy, circumventing IP blocking and various forms of censorship, and going beyond what rate limits would otherwise allow.

## Dependencies
Note: other environments will very likely work with no or minimal changes. But, this is what was used to develop TorScraper.
* Ubuntu Trusty 14.04
* Python 2.7.6
* Third party
  * PyYAML 3.10
  * pycurl 7.43.0
  * stem 1.4.0 

## Usage
See [tor\_scraper.py](tor_scraper.py) for example usage.

## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature.'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

## License
[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)
