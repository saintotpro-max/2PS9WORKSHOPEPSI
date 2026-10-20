













define config.name = _("RÉSILIENCE ALPHA")





define gui.show_name = True




define config.version = "0.1"





define gui.about = _("""Jeu Ren'Py du workshop EPSI RESILIENCE-ALPHA.

Chaque bouton agit sur la vraie plateforme (ou sur le simulateur, signalé en clair).

Interface : modèle du SDK Ren'Py 8.5.3 (licence MIT). Voir CREDITS.md.""")






define build.name = "alpha_double_face"


define build.version = "0.1"






define config.has_sound = True
define config.has_music = True
define config.has_voice = False

## Son d'apercu joue quand on regle le curseur "Sound Volume" dans les preferences
## (sinon le curseur semble "ne rien faire"). Son CC0 Kenney, voir CREDITS.md.
define config.sample_sound = "assets/audio/reprise.ogg"
























define config.enter_transition = dissolve
define config.exit_transition = dissolve




define config.after_load_transition = None




define config.end_game_transition = None
















define config.window = "auto"




define config.window_show_transition = Dissolve(.2)
define config.window_hide_transition = Dissolve(.2)







default preferences.text_cps = 0





default preferences.afm_time = 15
















define config.save_directory = "alpha_double_face-1"






define config.window_icon = "gui/window_icon.png"






init python:


    config.searchpath.append(config.renpy_base + "/sdk-fonts")
    build.classify_renpy("sdk-fonts/**", "all")
    build._sdk_fonts = True




















    build.classify('**~', None)
    build.classify('**.bak', None)
    build.classify('**/.**', None)
    build.classify('**/#**', None)
    build.classify('**/thumbs.db', None)









    build.documentation('*.html')
    build.documentation('*.txt')











define build.itch_project = "renpytom/the-question"



define config.console = True
