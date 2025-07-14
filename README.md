# Galaxy tips

A series of Galaxy tips to be displayed to users with the galaxy-tips webhook.

- Tips are written in plain HTML (you can use Galaxy's UI libraries like Bootstrap). Files must be named in an `<n>.html` numeric series e.g. `1.html`.
- Don't add anything except an `<n>.html` file to the `tips` folder, this will confuse the webhook when it tries to fetch a random.
- Images can be added to [./static/img/](./static/img/) but must be referenced with a full GitHub raw URL. See tip [1.html](./tips/1.html) for an example.
