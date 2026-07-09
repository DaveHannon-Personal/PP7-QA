# PP7 API Reference — PP7-QA Coverage Map

Quick reference for ProPresenter 7 API endpoints used by PP7-QA.  
Full interactive docs: **https://openapi.propresenter.com/**

Default base URL: `http://localhost:50001`

---

## Connection / Status

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/version` | Settings page health check |
| GET | `/v1/status/layers` | Dashboard layer status |

---

## Playlists

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/playlists` | Audit — enumerate all playlists |
| GET | `/v1/playlist/{playlist_id}` | Audit — get items in each playlist |

---

## Presentations

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/presentation/{uuid}` | Audit — fetch full presentation data including cue groups |
| GET | `/v1/presentation/active` | Available via API client |

---

## Libraries

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/libraries` | Available via API client |
| GET | `/v1/library/{library_id}` | Available via API client |

---

## Looks

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/looks` | Audit — fetch all looks for rule evaluation |
| GET | `/v1/look/current` | Available via API client |
| GET | `/v1/look/{id}` | Fix engine — fetch current look before update |
| PUT | `/v1/look/{id}` | Fix engine — update look properties |
| GET | `/v1/look/{id}/trigger` | Fix engine — `trigger_look` fix action |

---

## Themes

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/themes` | Audit — fetch all themes for rule evaluation |
| GET | `/v1/theme/{id}` | Available via API client |
| PUT | `/v1/theme/{id}/slides/{theme_slide}` | Fix engine — update theme slide |

---

## Props

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/props` | Audit — fetch all props |
| GET | `/v1/prop/{id}` | Fix engine — fetch before update |
| PUT | `/v1/prop/{id}` | Fix engine — update prop properties |

---

## Macros

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/macros` | Audit — fetch all macros |
| GET | `/v1/macro/{id}` | Fix engine — fetch before update |
| PUT | `/v1/macro/{id}` | Fix engine — update macro properties |

---

## Messages

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/messages` | Audit — fetch all messages |
| PUT | `/v1/message/{id}` | Fix engine — update message properties |

---

## Groups

| Method | Endpoint | PP7-QA Usage |
|---|---|---|
| GET | `/v1/groups` | Available via API client |

---

## Endpoints Not Currently Used (available for future rules)

| Category | Notable Endpoints |
|---|---|
| Stage | `/v1/stage/layouts`, `/v1/stage/screens` |
| Capture | `/v1/capture/status`, `/v1/capture/settings` |
| Timers | `/v1/timers` |
| Audio | `/v1/audio/playlists` |
| Media | `/v1/media/playlists` |
| Masks | `/v1/masks` |
| Video Input | `/v1/video_inputs` |
| Announcement | `/v1/announcement/active` |
| Transport | `/v1/transport/{layer}/time` |

---

## PP7 Object ID Format

ProPresenter 7 returns IDs as objects with a `uuid` property:

```json
{
  "id": {
    "uuid": "A1B2C3D4-...",
    "name": "optional display name"
  }
}
```

The PP7-QA API client extracts the `uuid` string for all operations.

---

## PP7 Name Format

Many string fields in PP7 are returned as:

```json
{
  "name": {
    "string": "My Presentation",
    "isRTF": false
  }
}
```

When writing condition `field` values, use `name.string` to target the plain-text name.
