# Register generated dashboards in Home Assistant

NikaS House `0.1.0` can export review-only Lovelace YAML but does not edit Home Assistant `.storage` or `configuration.yaml` automatically.

## Generated files

After **Generate dashboards / Сгенерировать панели** succeeds, runtime output is written under:

```text
/config/nikas_house/generated/
```

For the House manifest the integration writes:

- `<manifest-id>.yaml` — deterministic Lovelace dashboard candidate;
- `<manifest-id>.meta.json` — RenderTrace with source bindings, semantic model and SHA-256.

It also writes:

```text
/config/nikas_house/generated/lovelace_configuration_snippet.yaml
```

The snippet uses Home Assistant's supported YAML dashboard configuration shape.

The House custom panel is not included in the snippet because it is registered by the
integration only at `/dashboard-house-v13/home`. If that route is occupied, registration
stops without selecting a fallback. NikaS House preserves the existing YAML
`Дом`, `Помещения`, `Действия` and `Инфраструктура` registrations and never removes or
replaces them.

## Important safety rule

The generated snippet is **merge input**, not an instruction to overwrite `configuration.yaml`.

If `configuration.yaml` already contains a top-level `lovelace:` section, merge the generated `dashboards:` entries into it. Preserve existing resources, resource mode, and other dashboards.

The generic shape below documents the supported exporter, although this House-only
repository does not currently ship a non-specialized dashboard manifest:

```yaml
lovelace:
  dashboards:
    dashboard-example:
      mode: yaml
      filename: nikas_house/generated/example.yaml
      title: Example
      show_in_sidebar: true
      require_admin: false
```

Home Assistant requires additional YAML dashboard URL keys to contain a hyphen. NikaS House validates this rule when exporting the snippet.

## Deployment boundary

The integration deliberately stops before applying the snippet. It does not:

- edit `configuration.yaml`;
- write Home Assistant `.storage` Lovelace files;
- register internal Lovelace collections through private Home Assistant APIs;
- replace existing dashboards.

This keeps generation deterministic and reviewable while dashboard registration remains an explicit Home Assistant configuration change.

## Verification sequence

1. Ensure **Source status / Состояние источников** is `valid / Корректно`.
2. Press **Generate dashboards / Сгенерировать панели**.
3. Check button attributes for generated file paths, dashboard SHA-256, and registration snippet path.
4. Review the generated YAML and RenderTrace.
5. Merge the registration entry into `configuration.yaml` only after review.
6. Validate Home Assistant configuration and restart/reload as required.
7. Keep the previous generated candidate/trace available for rollback and semantic diff.
