from enum import Enum

class StatutDossier(str, Enum):
    COURRIER = "COURRIER"
    SPFEI_ADMIN = "SPFEI_ADMIN"
    SCVAA = "SCVAA"
    NON_CONFORME = "NON_CONFORME"
    SPFEI_TITRE = "SPFEI_TITRE"
    CONSERVATION = "CONSERVATION"

class Conformite(str, Enum):
    CONFORME = "CONFORME"
    NON_CONFORME = "NON_CONFORME"

class Genre(str, Enum):
    MASCULIN = "Masculin"
    FEMININ = "Féminin"

class StatutSMS(str, Enum):
    ENVOYE = "ENVOYE"
    ECHEC = "ECHEC"
    SIMULE = "SIMULE"

class TypeSMS(str, Enum):
    NON_CONFORMITE = "NON_CONFORMITE"
    FINALISATION = "FINALISATION"

class TypeFichier(str, Enum):
    PDF = "PDF"
    IMAGE = "IMAGE"
    AUTRE = "AUTRE"
