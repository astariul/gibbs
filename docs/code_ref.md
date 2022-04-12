# Code reference

## API

::: gibbs.hub
    selection:
      members: Hub
    rendering:
      show_root_heading: False
      show_root_toc_entry: False
      heading_level: 3

::: gibbs.worker
    selection:
      members: Worker
    rendering:
      show_root_heading: False
      show_root_toc_entry: False
      heading_level: 3

## Internal

::: gibbs.hub
    selection:
      filters: ["!Response", "!Hub"]
    rendering:
      show_root_heading: False
      show_root_toc_entry: False
      heading_level: 3

## Constants

::: gibbs.hub
    selection:
      filters:
      - "!.*"
      - "^[A-Z][A-Z_0-9]*$"
    rendering:
      show_if_no_docstring: True
      show_root_heading: False
      show_root_toc_entry: False
      members_order: "source"
      heading_level: 3


::: gibbs.worker
    selection:
      filters:
      - "!.*"
      - "^[A-Z][A-Z_0-9]*$"
    rendering:
      show_if_no_docstring: True
      show_root_heading: False
      show_root_toc_entry: False
      members_order: "source"
      heading_level: 3
