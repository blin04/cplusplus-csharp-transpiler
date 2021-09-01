
# klase za AST
class AstDeclaration:
    def __init__(self):
        self.type = ""
        self.variable = ""
        self.value = ""
        self.array = False
        self.array_size = ""

    # generise ekvivalentan C# kod
    def generate_code(self):
        s = self.type
        if self.array: # ukoliko je definicija niza u pitanju, dodaj [] (kao int[])
            s += "[]"

        s += " " + self.variable

        if self.array:                                      # ako je dekl niza up pitanju, moramo da dodamo
            s += " = new int[" + self.array_size + "]"     # new int[size];

        if self.value != "":                                # ako je value true, to znaci da se dodeljuje neka vrednost
            if self.array:                                  # ako je niz u pitanju, ide drugacija sintaksa
                # zbog C# sintakse, niz ne mozemo inicijalizovati
                # u istoj liniji u kojoj ga deklarisemo
                # zato dodajemo novu liniju
                s += ";\n" + self.variable + " = " + self.value
            else:                                           # u suprotnom, u pitanju je obicna promenljiva
                s += " = "
                s += self.value
        s += ";"
        return s


class AstMethodDeclaration:
    def __init__(self):
        self.virtual = None         # ovo je za kasnije
        self.override = False
        self.specifier = None       # TODO: namestiti preskakanje private metoda
        self.type = None        # ako type ostane none, u pitanju je konstruktor
        self.name = ""

    def generate_code(self):
        kod = ""

        if self.virtual is not None:
            kod += self.virtual + " "

        if self.override:
            kod += "override "

        if self.type is not None:
            kod += self.type + " "

        kod += self.name + "()"
        return kod


class AstFieldDeclaration:
    def __init__(self):
        self.abstract = False
        self.type = None
        self.name = ""
        self.value = None
        self.array_size = "-1"

    def generate_code(self):
        kod = ""
        if self.array_size != "-1":
            kod += self.type + "[] " + self.name + " = new " + self.type + "[" + self.array_size + "]"
            return kod

        # ako je u pitanju definicija pure virtual metode, parser je zapravo vidi kao polje - zato imamo ovo self.abstract
        # koje nam kaze da izgenerisemo apstraktnu metodu u c#
        if self.abstract:
            kod += "abstract " + self.type + " " + self.name + "()"
            return kod

        if self.type is not None:
            kod += self.type + " "
        kod += self.name

        if self.value is not None:
            kod += " = " + self.value
        return kod


# klasa za definiciju klasa
class AstClass:
    def __init__(self):
        self.kod = ""               # konacan kod koji ce biti izgenerisan
        self.name = ""
        self.abstract = False       # da li je trenutna klasa apstraktna
        self.interface = False      # da li je potrebno izgenerisati interfejs za ovu klasu
        self.parent_classes = []        # za svaku baznu klasu generisemo objekat, metode i na kraju implicit operator
        self.allDeclarations = []       # u ovu listu cemo staviti i polja i metode, redom kojim se pojavljuju
        self.return_dictionary = {
            "int": "0",
            "char": "'a'",
            "long": "0",
            "string": "str",
            "dobule": "3.14159",
            "float": "3.14159",
            "bool": "true"
        }
        return

    def check_if_overriden(self, method_name):     # helper funkcija za proveravanje da li je metoda overrajduvana
        for method in self.allDeclarations:
            if isinstance(method, AstMethodDeclaration):
                if method.name == method_name:
                    return True
        return False

    def check_virutal(self, method, parent):
        if len(self.parent_classes) == 0:
            return
        # proveravamo sve metode klase koja je direktno nasledjena da proverimo da li je tr metoda deklarisana kao virtuelna
        for parent_method in parent.allDeclarations:
            if isinstance(parent_method, AstMethodDeclaration):
                if parent_method.name == method.name and parent_method.virtual is not None:
                    method.override = True
            elif isinstance(parent_method, AstFieldDeclaration):
                # parser pure virtual metode vidi kao deklaraciju polja pa zato moramo proveriti i AstField objekte
                if parent_method.name == method.name and parent_method.abstract:
                    method.override = True

    def generate_inheritance(self, direct_name):
        # za svaki parent izgenerisi objekat i posle izgenerisi potrebne metode
        for parent in self.parent_classes:
            if isinstance(parent, AstClass):
                if parent.name == direct_name:
                    continue
                if parent.abstract:
                    # apstraktne klase ne mogu definisati svoje objekte - tako da ne mozemo pozivati njene metode
                    # preko ugnjezdenog objekta (pretpostavka je da su sve metode apstraktne klase vec overrajdovane)
                    continue

                necessary = False
                add_code = ""
                object_name = parent.name + "Part"
                self.kod += "    public " + parent.name + " " + object_name + " = new " + parent.name + "();\n"

                for method in parent.allDeclarations:
                    if isinstance(method, AstMethodDeclaration):
                        if method.type is None:
                            continue
                        if (self.check_if_overriden(method.name) and method.virtual) or method.specifier == "private":
                            # ako je ova metoda vec overrajdovana ili privatna, preskoci je
                            continue
                        necessary = True
                        add_code += "   " + " public " + method.type + " " + method.name + "()\n"
                        add_code += "    {\n"
                        if method.type == "void":
                            add_code += "        " + object_name + "." + method.name + "();\n"
                        else:
                            add_code += "        " + method.type + " result = " + object_name + "." + method.name + "();\n"
                            add_code += "        return result;\n"
                        add_code += "    }\n"
                if necessary:
                    self.kod += add_code
        return

    def generate_interface(self):
        interface_name = "I" + self.name        # IClassName
        self.kod += "interface " + interface_name + "\n"
        self.kod += "{\n"

        for method in self.allDeclarations:
            if isinstance(method, AstMethodDeclaration):
                if method.type is None:
                    # u pitanju je konstruktor koji preskacemo
                    continue
                if method.specifier == "private":
                    # preskacemo privatne metode
                    continue

                self.kod += "    " + method.type + " " + method.name + "();\n"
                # svaki member interfejsa mora da bude public

        self.kod += "}\n"

    def set_specifiers(self):
        specifier = "private"
        for decl in self.allDeclarations:
            if isinstance(decl, AstMethodDeclaration):
                decl.specifier = specifier
            elif isinstance(decl, str):
                specifier = decl

    def generate_code(self):
        self.set_specifiers()

        if self.interface:
            self.generate_interface()
        if self.abstract:
            self.kod += "abstract "
        self.kod += "class " + self.name

        direct = None
        if len(self.parent_classes) > 0:
            # klasa direknto nasledjuje poslednju klasu, ostale ugnjezdujemo
            direct = self.parent_classes[-1]
            for parent in self.parent_classes:
                if parent.abstract:
                    direct = parent

            self.kod += " : " + direct.name     # moramo prvu naslediti klasu pa tek onda interfejse

            if self.interface:  # ako je za ovu klasu izgenersian interfejs, onda ga treba naslediti
                self.kod += ", I" + self.name
            for parent in self.parent_classes:
                if isinstance(parent, AstClass):
                    if parent == direct:    # apstraktnu klasu nasledjujemo direktno
                        continue
                    parent_interface_name = "I" + parent.name
                    self.kod += ", " + parent_interface_name
            self.kod += "\n"

        else:
            # ako nema nasledjivanja, samo prelazimo u novi red
            self.kod += "\n"

        self.kod += "{\n"        # otvaramo zagradu za definiciju klase

        specifier = "private"  # dok ne naidjemo na izricitu deklaraciju access specifiera, onda je ta prom. priv.
        if self.name == "Program":
            specifier = None

        for decl in self.allDeclarations:
            if isinstance(decl, AstFieldDeclaration):
                self.kod += "    " + specifier + " " + decl.generate_code() + ";\n"
            elif isinstance(decl, AstMethodDeclaration):
                self.kod += "    "  # tabovanje
                if specifier is not None:
                    if self.interface:
                        # sve metode koje implementira interfejs moraju biti public - a interfejs implementira sve
                        # metode osim privatnih
                        if decl.specifier != "private":
                            decl.specifier = "public"
                    if decl.specifier != "":
                        self.kod += decl.specifier + " "      # ako nije u pitanju klasa Program, imamo neki access specifier
                self.check_virutal(decl, direct)
                self.kod += decl.generate_code() + "\n"
                self.kod += "    {\n"
            #    self.kod += "       // method's body can be filled as you wish\n"
                self.kod += "       Console.WriteLine(" + '"class ' + self.name + ': method ' + decl.name + '"' + ");\n"
                if decl.name != "Main" and decl.type != "void" and decl.type is not None:
                    self.kod += "       return " + self.return_dictionary[decl.type] + ";\n"
                self.kod += "    }\n"
            else:
                # ako nije ni AstFieldDeclaration ni AstMethodDeclaration, onda je u pitanju promena access specifiera
                specifier = str(decl)

        self.generate_inheritance(direct.name if direct is not None else None)

        self.kod += "}\n"        # zatvaramo zagradu za definiciju klase
        return self.kod
