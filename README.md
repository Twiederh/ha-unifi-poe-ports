# UniFi PoE Ports für Home Assistant

Eigene Home-Assistant-Integration (`custom_component`), die alle **PoE-fähigen Ports** deiner UniFi-Switches als `switch`-Entities in Home Assistant bereitstellt – ein Port pro Entity, benannt nach dem **Port-Label**, das du im UniFi Network-Controller vergeben hast. Damit lässt sich PoE pro Port ganz normal per Automation, Skript oder Dashboard ein-/ausschalten.

Die Integration spricht direkt mit der UniFi Network Application (über dieselbe `aiounifi`-Bibliothek, die auch die offizielle UniFi-Integration von Home Assistant nutzt) und pollt den Controller alle 30 Sekunden.

## Was wird angelegt?

- Pro UniFi-Switch ein Gerät in Home Assistant (Name = Gerätename aus UniFi).
- Pro Port dieses Switches, der laut Controller PoE nutzt (`port_poe`), ein `switch`-Entity darunter.
- Der Entity-Name ist exakt das **Port-Label** aus dem UniFi Network-Controller (Geräte → dein Switch → Ports → Port anklicken → Feld "Name"). Hast du keinen eigenen Namen vergeben, zeigt UniFi dort z. B. "Port 5" an – genau das erscheint dann auch in Home Assistant.
- Attribute je Entity: `poe_mode` (`auto`/`pasv24`/`passthrough`/`off`), `poe_class`, `poe_power_w`, `port_idx`, `switch_name`.

Beim Ausschalten wird der Port auf `poe_mode: off` gesetzt. Beim Wiedereinschalten stellt die Integration den zuletzt beobachteten aktiven Modus wieder her (z. B. `auto`); wurde seit dem Neustart von Home Assistant noch kein aktiver Modus gesehen, wird `auto` verwendet.

## Installation

### Über HACS (empfohlen)

1. HACS → Integrationen → Menü oben rechts → *Benutzerdefinierte Repositories*.
2. Repository-URL `https://github.com/Twiederh/ha-unifi-poe-ports` mit Kategorie **Integration** hinzufügen.
3. "UniFi PoE Ports" installieren und Home Assistant neu starten.

### Manuell

1. Ordner `custom_components/unifi_poe` aus diesem Repository nach `<config>/custom_components/unifi_poe` kopieren.
2. Home Assistant neu starten.

## Einrichtung

1. Einstellungen → Geräte & Dienste → Integration hinzufügen → "UniFi PoE Ports" suchen.
2. Angeben:
   - **Host/IP** des Controllers (bei einem UniFi-OS-Gerät wie UDM/UDM-Pro/Cloud Gateway die IP davon, bei separater Controller-Software die IP des Controller-Hosts).
   - **Port**: `443` für UniFi-OS-Geräte (Standard hier), `8443` für klassische Network-Controller-Software.
   - **Benutzername/Passwort**: ein lokaler UniFi-Account. Empfehlenswert ist ein eigener, dedizierter Account mit Rolle *Limited Admin*/*Site Admin* im Netzwerk-App, statt des Ubiquiti-Cloud-Kontos.
   - **Site-ID**: normalerweise `default`, außer du hast mehrere Sites angelegt.
   - **SSL-Zertifikat prüfen**: aus lassen, solange dein Controller ein selbstsigniertes Zertifikat verwendet (Standard bei UDM/Cloud Gateway).

Die Integration meldet sich beim Speichern einmal testweise am Controller an, um die Zugangsdaten zu prüfen.

## Beispiel-Automation

Port mit dem UniFi-Label "Kamera Garage" per Automation abschalten:

```yaml
automation:
  - alias: "PoE für Kamera Garage nachts abschalten"
    triggers:
      - trigger: time
        at: "23:00:00"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.switch_keller_kamera_garage
```

Den tatsächlichen Entity-Namen findest du unter Einstellungen → Geräte & Dienste → Entitäten, gefiltert nach der Integration "UniFi PoE Ports" – er richtet sich nach Gerätename + Port-Label.

## Hinweise

- Erfordert Netzwerkzugriff von Home Assistant auf den UniFi-Controller (Port 443 bzw. 8443).
- Port-Overrides werden von der Integration additiv gesetzt (bestehende Port-Konfiguration/`portconf_id` bleibt erhalten) – analog zum Verhalten der offiziellen UniFi-Integration.
- Getestet gegen `aiounifi` 74 (aktuelle Version zum Zeitpunkt der Erstellung). Bei Problemen nach einem UniFi-Network-Update ggf. `aiounifi`-Version in `manifest.json` aktualisieren.
