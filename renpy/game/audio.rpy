# Signatures sonores (sons CC0 Kenney, voir CREDITS.md). Un son par type d'attaque,
# plus alerte et reprise. Joues aux temps forts de la campagne et du duel.

init python:
    SON_ATTAQUE = {
        1: "assets/audio/attaque_charge.ogg",
        2: "assets/audio/attaque_lentes.ogg",
        3: "assets/audio/attaque_reseau.ogg",
        4: "assets/audio/attaque_injection.ogg",
    }
    SON_ALERTE = "assets/audio/alerte.ogg"
    SON_REPRISE = "assets/audio/reprise.ogg"

    def jouer(chemin):
        """Joue un son court sur le canal des effets ; sans jamais faire echouer le jeu."""
        try:
            if chemin and renpy.loadable(chemin):
                renpy.sound.play(chemin)
        except Exception:
            pass

    def son_attaque(niveau):
        jouer(SON_ATTAQUE.get(niveau))
