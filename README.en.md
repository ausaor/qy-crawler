# QY Crawler

This is an open-source crawler project hosted on the `Gitee` platform, mainly used to crawl specified hero information and detailed hero information from the web.

## Directory Structure

```
.
├── .gitignore
├── api
│   └── wzry.py
├── config
│   └── settings.py
├── main.py
├── orm
│   ├── __init__.py
│   └── models.py
└── static
    └── htmls
        └── wzry-hero-list.html
```

## Main Features

- Provides `/crawler/heros` interface for crawling hero lists.
- Provides `/crawler/heroDetail` interface for crawling detailed hero information.

## Data Models

- `HeroInfo`: Stores basic information about heroes.
- `HeroSkin`: Stores skin information about heroes.

## Technologies Used

- Uses the `async` asynchronous framework to provide web interfaces.
- Uses the `Model` class for database model definitions.

## Static Resources

- `static/htmls/wzry-hero-list.html`: Displays the crawled hero list.

## Configuration File

- `config/settings.py`: The configuration file for the project.

## Entry Point

- `main.py`: The entry file for the project.

## How to Contribute

Feel free to submit Issues and Pull Requests.

## License

This project uses the MIT License. For details, please check the LICENSE file in the project root directory.