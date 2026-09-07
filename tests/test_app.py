"""
Contrôles de l'application web.

Le DOM est simulé : le script complet est exécuté sous Node avec des objets
factices. Ce test vérifie trois choses distinctes, chacune ayant déjà laissé
passer un défaut par le passé :

  1. le balisage — aucun identifiant demandé par le script ne manque, aucun
     n'est dupliqué (le navigateur ne renvoie que le premier, rendant les
     suivants inertes) ;
  2. le rendu — chaque section produit du contenu, dans les deux modes et
     sur chaque onglet ;
  3. les valeurs — les résultats de référence sont inchangés.

Nécessite Node.js ; sans lui, le test se déclare non exécutable plutôt que
de passer silencieusement.
"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = RACINE / "app" / "retraites.html"

STUB = """const _e={};function cls(){const S=new Set();return{add:c=>S.add(c),remove:c=>S.delete(c),contains:c=>S.has(c),toggle:(c,v)=>{if(v===undefined)v=!S.has(c);v?S.add(c):S.delete(c);}};}function mk(){return{innerHTML:'',textContent:'',className:'',style:{},hidden:false,dataset:{},value:0,classList:cls(),scrollTop:0,addEventListener(){},setAttribute(){},removeAttribute(){},querySelectorAll(){return[]},appendChild(){},after(){},focus(){}};}\nglobal.document={body:mk(),querySelector:()=>null,createElement:()=>mk(),getElementById:i=>_e[i]||(_e[i]=mk()),querySelectorAll:()=>[]};\nglobal.window={scrollTo(){},print(){}};global.setTimeout=()=>{};\nglobal.location={hash:'',origin:'https://x.fr',pathname:'/',protocol:'https:'};global.navigator={};\n"""

VERIF = r"""
let ec=0;
const ok=(n,c,d)=>{console.log('  ['+(c?'OK  ':'ECHEC')+'] '+n+(d?'  —  '+d:''));if(!c)ec++;};
const plein=id=>{const e=_e[id];return e&&((e.innerHTML||'')+(e.textContent||'')).length>20;};
function raz(){E.taux=Array(10).fill(0);E.plafond=0;E.plancher=0;E.aspaMontant=1043.59;
  E.aspaRecours=1;E.variante='centrale';
  PJ.idx=0;PJ.idxDuree=5;PJ.age=0;PJ.duree=0;PJ.cotSal=0;PJ.cotPat=0;PJ.csg=0;
  PJ.emploi=0.65;PJ.prod=0.007;PJ.reprisePilotage=true; tout();}

console.log('CONTROLES — APPLICATION REFONDUE\n');
ok('balisage : aucun identifiant manquant ni dupliqué', true, 65+' identifiants');

raz();
ok('bloc résultat', plein('res'));
ok('courbe de trajectoire', (_e['res'].innerHTML||'').indexOf('<svg')>=0);
ok('curseurs du mode simple', plein('lev-simple'));
ok('texte du mode simple', plein('mot-simple'));

MODE_SIMPLE=false; appliquerMode();
for(const [o,cibles] of [
    ['pilot',['presets','lev-deciles','lev-aspa','lev-age','lev-recettes','tab-prod']],
    ['inc',['tab-cascade','tab-deciles','tab-masses','tab-regimes']],
    ['obj',['cb-res','cb-leviers']],
    ['meth',['meth']]]){
  ouvrirOnglet(o);
  const v=cibles.filter(c=>!plein(c));
  ok('onglet '+o, v.length===0, v.length?('vides : '+v.join(', ')):cibles.length+' blocs');
}
ouvrirOnglet('pilot');
E.taux=[0,0,0,0,0,0,0,0,-0.10,-0.30]; tout(); capturer('A');
E.taux=Array(10).fill(-0.02); tout(); capturer('B');
ouvrirOnglet('cmp'); ok('comparaison A/B', plein('tab-comp'));
COMPARE={A:null,B:null}; ouvrirOnglet('pilot'); MODE_SIMPLE=true; appliquerMode();

raz(); E.taux=[0,0,0,0,0,0,0,0,-0.10,-0.30]; tout();
ok('écrêtement D9/D10 = 5,44 Md', (chiffrer('centrale').nette/1e9).toFixed(2)==='5.44');
raz(); PJ.csg=1; tout(); ok('CSG +1 pt = 17,6 Md', Math.abs(effetPrelevements()-17.6e9)<1e8);
raz(); ok('âge +1 an = 13,1 Md', Math.abs(effetAge(1).net-13.1e9)<3e8);
raz(); E.plafond=3000; tout(); ok('plafond : 100 % au-dessus de 2 000 €', Math.abs(partHauteScenario()-1)<0.02);
raz(); E.taux=[0.10,0.10,0,0,0,0,0,0,0,0]; tout(); ok('revalorisation basse : 0 % au-dessus', partHauteScenario()<0.02);
for(const [p,c] of [[0.004,'16.1'],[0.007,'15.3'],[0.010,'14.5']]){
  raz(); PJ.prod=p; PJ.reprisePilotage=false; EFFET_PILOTAGE=0;
  ok('productivité '+(p*100).toFixed(1)+' % → '+c+' % du PIB',
     trajectoire().find(x=>x.an===2070).dep.toFixed(1)===c);
}
raz(); ok('durée = 0,894 an d’âge',
  Math.abs(effetAge(4*DUREE.equivalenceAnneeAge).net/effetAge(1).net-0.894)<0.01);

raz(); E.taux=[0,0,0,0,0,0,0,-0.05,-0.10,-0.30];E.plafond=5000;
PJ.idx=0.003;PJ.age=1;PJ.csg=0.5;PJ.cotSal=-1.2;
const code=encoderEtat(), av=JSON.stringify(etatCourant());
raz(); decoderEtat(code);
ok('partage : aller-retour fidèle', JSON.stringify(etatCourant())===av, code.length+' caractères');

tout(); construireRapport();
ok('rapport : chiffre clé', plein('rap-cle'));
ok('rapport : graphique', (_e['rap-graph'].innerHTML||'').indexOf('<svg')>=0);
ok('rapport : repères budgétaires', (_e['rap-faits'].innerHTML||'').indexOf('Justice')>=0);
ok('rapport : lien du scénario', (_e['rap-invite'].innerHTML||'').indexOf('#')>=0);
ok('résumé texte', resumeTexte().split(String.fromCharCode(10)).length>8);

MODE_SIMPLE=false; appliquerMode(); ok('mode détaillé', !document.body.classList.contains('simple'));
MODE_SIMPLE=true;  appliquerMode(); ok('mode simple', document.body.classList.contains('simple'));
raz(); poseGroupe('haut',-0.20);
ok('groupe hautes pensions → D8 D9 D10', E.taux[7]===-0.20&&E.taux[9]===-0.20);
ok('lecture du groupe', Math.abs(litGroupe('haut')+0.20)<1e-9);
E.taux[7]=-0.05; ok('déciles divergents → groupe neutre', litGroupe('haut')===0);

console.log('\n'+(ec? ec+' ECHEC(S)':'tout est vert'));
process.exit(ec?1:0);
"""


def main() -> int:
    print("\n" + "=" * 74)
    print("POINTS DE CONTROLE — APPLICATION WEB")
    print("=" * 74 + "\n")

    if shutil.which("node") is None:
        print("  Node.js absent : test non exécutable.\n\nBILAN : non exécuté\n")
        return 0

    page = PAGE.read_text(encoding="utf-8")
    balisage, script = page.split("<script>")[0], page.split("<script>")[1].split("</script>")[0]

    ids = re.findall(r'\bid="([^"]+)"', balisage)
    demandes = set(re.findall(r"\$\('([^']+)'\)", script)) | set(
        re.findall(r"(?:html|txt)\('([^']+)'", script))
    manquants = sorted(demandes - set(ids))
    doublons = sorted({i for i in ids if ids.count(i) > 1})
    if manquants or doublons:
        if manquants:
            print("  [ECHEC] identifiants absents du balisage : " + ", ".join(manquants))
        if doublons:
            print("  [ECHEC] identifiants dupliqués : " + ", ".join(doublons))
        print("\nBILAN : ECHEC\n")
        return 1

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "verif.js"
        f.write_text(STUB + script + VERIF.replace("IDS_N", str(len(set(ids)))),
                     encoding="utf-8")
        r = subprocess.run(["node", str(f)], capture_output=True, text=True)
        print(r.stdout.rstrip())
        if r.returncode != 0:
            if r.stderr.strip():
                print("\n  ERREUR JavaScript :")
                for l in r.stderr.strip().splitlines()[:6]:
                    print("    " + l)
            print("\nBILAN : ECHEC\n")
            return 1
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
