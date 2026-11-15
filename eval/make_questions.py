"""Writes eval/questions.json. Every answerable question names the article it should come from,
regular expressions that must all appear in the same passage (the 'gold' evidence), and groups of
keywords where at least one word from each group should appear in a correct answer."""
import json

A = "answerable"
# (gold article, question, [regexes that must all match one passage], [[any-of keywords], ...])
ANSWERABLE = [
    ("Apple scab", "Which fungus causes apple scab?", [r"Venturia inaequalis"], [["venturia inaequalis"]]),
    ("Apple scab", "Where does the apple scab fungus spend the winter?", [r"overwinter"], [["leaves", "leaf litter", "fallen"]]),
    ("Gymnosporangium juniperi-virginianae", "Which two kinds of plants does cedar apple rust need to complete its life cycle?", [r"juniper|cedar", r"apple"], [["apple"], ["juniper", "cedar"]]),
    ("Gymnosporangium juniperi-virginianae", "What do cedar apple rust symptoms look like on apple leaves?", [r"yellow|orange"], [["yellow", "orange"]]),
    ("Alternaria solani", "What do early blight lesions on tomato leaves look like?", [r"target|bullseye|concentric"], [["target", "bullseye", "bull's-eye", "concentric"]]),
    ("Alternaria solani", "Besides tomato, which crop does early blight commonly affect?", [r"potato"], [["potato"]]),
    ("Phytophthora infestans", "Which historical event was caused by potato late blight?", [r"famine"], [["famine"]]),
    ("Phytophthora infestans", "What kind of organism is Phytophthora infestans?", [r"oomycete"], [["oomycete", "water mould", "water mold"]]),
    ("Phytophthora infestans", "What weather conditions favour the spread of late blight?", [r"humid|moist|cool|wet"], [["cool", "moist", "humid", "wet"]]),
    ("Citrus greening disease", "Which insect spreads citrus greening disease?", [r"psyllid"], [["psyllid"]]),
    ("Citrus greening disease", "Can citrus greening disease be cured?", [r"cure|no known|incurable|no effective"], [["no", "not", "cannot", "incurable"]]),
    ("Diaphorina citri", "Where is the Asian citrus psyllid found?", [r"Asia"], [["asia"]]),
    ("Tomato yellow leaf curl virus", "How is tomato yellow leaf curl virus transmitted?", [r"whitefl|Bemisia"], [["whitefl", "bemisia"]]),
    ("Tomato yellow leaf curl virus", "What symptoms does tomato yellow leaf curl virus cause?", [r"curl|cupp", r"yellow|chlorosis"], [["curl", "cupp"], ["yellow", "chlorosis"]]),
    ("Tomato yellow leaf curl virus", "How can tomato yellow leaf curl virus be managed?", [r"resistan|insecticide|vector"], [["resistan", "vector", "whitefl", "insecticide"]]),
    ("Tomato mosaic virus", "How does tomato mosaic virus spread between plants?", [r"seed|contact|mechanical|touch|tools|hands"], [["seed", "contact", "mechanical", "touch", "tools", "hands", "handling"]]),
    ("Tomato leaf mold", "Which fungus causes tomato leaf mold?", [r"Passalora fulva|Cladosporium fulvum"], [["passalora", "cladosporium"]]),
    ("Tomato leaf mold", "What humidity levels favour tomato leaf mold?", [r"humidity"], [["humid"]]),
    ("Septoria lycopersici", "What do Septoria leaf spot lesions on tomato look like?", [r"spot|lesion"], [["spot", "lesion"]]),
    ("Black rot (grape disease)", "Which fungus causes black rot of grape?", [r"Guignardia bidwellii|Phyllosticta"], [["guignardia", "phyllosticta"]]),
    ("Black rot (grape disease)", "How does grape black rot survive between seasons?", [r"overwinter|mummi"], [["mummi", "overwinter", "canes"]]),
    ("Black rot (grape disease)", "What cultural practices help control grape black rot?", [r"prun|canopy|sanit|mummi|remov"], [["prun", "canopy", "sanit", "remov", "mummi"]]),
    ("Corn grey leaf spot", "What does gray leaf spot of corn look like?", [r"rectangular|grey|gray"], [["rectangular", "gray", "grey", "tan"]]),
    ("Corn grey leaf spot", "How can gray leaf spot of corn be managed?", [r"rotation|tillage|resistan"], [["rotation", "tillage", "resistan", "hybrid"]]),
    ("Northern corn leaf blight", "What shape are the lesions of northern corn leaf blight?", [r"cigar|elliptical|boat"], [["cigar", "elliptical", "boat"]]),
    ("Northern corn leaf blight", "Which fungus causes northern corn leaf blight?", [r"Exserohilum turcicum|Setosphaeria turcica"], [["exserohilum", "setosphaeria"]]),
    ("Puccinia sorghi", "What are the symptoms of common rust on corn?", [r"pustule"], [["pustule"]]),
    ("Diplocarpon earlianum", "What does strawberry leaf scorch look like?", [r"purple"], [["purple"]]),
    ("Diplocarpon earlianum", "How does the strawberry leaf scorch fungus survive the winter?", [r"overwinter"], [["leaves", "infected", "debris", "overwinter"]]),
    ("Corynespora cassiicola", "Which crops can Corynespora cassiicola infect?", [r"tomato|cucumber|soybean|papaya|rubber"], [["tomato", "cucumber", "soybean", "papaya", "rubber"]]),
    ("Botryosphaeria obtusa", "How is black rot of apple controlled?", [r"prun|remov|sanit|fungicide"], [["prun", "remov", "sanit", "fungicide"]]),
    ("Erysiphaceae", "What does powdery mildew look like on leaves?", [r"white|powder"], [["white", "powder"]]),
    ("Erysiphaceae", "What weather conditions favour powdery mildew?", [r"humid|dry|warm|temperature"], [["humid", "dry", "warm", "temperature"]]),
    ("Tetranychus urticae", "What do two-spotted spider mites feed on?", [r"sap|cell|leaves|plants"], [["sap", "cell", "leaves", "plants"]]),
    ("Whitefly", "How do whiteflies damage plants?", [r"sap|honeydew|virus"], [["sap", "honeydew", "virus"]]),
    ("Whitefly", "How do whiteflies spread plant viruses?", [r"virus"], [["virus"]]),
    ("Crop rotation", "How does crop rotation help reduce pests and diseases?", [r"pest|disease"], [["pest", "disease"]]),
    ("Crop rotation", "What is crop rotation?", [r"sequen|success|series|alternat"], [["sequen", "success", "series", "alternat", "different crops"]]),
    ("Fungicide", "What are fungicides used for?", [r"kill|inhibit|control|fung"], [["kill", "inhibit", "control", "fung"]]),
    ("Integrated pest management", "What are the main principles of integrated pest management?", [r"prevention|monitor|threshold|identif"], [["prevention", "monitor", "threshold", "identif"]]),
    ("Mulch", "How does mulch help plants and soil?", [r"moisture|weed|temperature"], [["moisture", "weed", "temperature"]]),
    ("Plant disease resistance", "What is pattern-triggered immunity in plants?", [r"pattern"], [["pattern", "recogni"]]),
    ("Plant disease resistance", "How do physical barriers help plants resist disease?", [r"cuticle|wax|cell wall|bark"], [["cuticle", "wax", "cell wall", "bark"]]),
    ("Plant virus", "How do insects transmit plant viruses?", [r"aphid|whitefl|insect|vector"], [["aphid", "whitefl", "insect", "vector"]]),
    ("Plant disease epidemiology", "What three elements are needed for a plant disease epidemic?", [r"host", r"pathogen|environment"], [["host"], ["pathogen"], ["environment"]]),
    ("Leaf spot", "What can cause leaf spots on plants?", [r"fung|bacteri|virus"], [["fung", "bacteri", "virus"]]),
    ("Oomycete", "Why are oomycetes not true fungi?", [r"cellulose|not.*fung|fungus-like|water mould|water mold"], [["cellulose", "not", "fungus-like", "water mould", "water mold"]]),
    ("Rust (fungus)", "What are rust fungi?", [r"rust"], [["fung", "pathogen", "plant"]]),
    ("Bacterial leaf spot of peppers and tomato", "Which bacteria cause bacterial spot of tomato and pepper?", [r"Xanthomonas"], [["xanthomonas"]]),
    ("Xanthomonas arboricola pv. pruni", "Which fruit trees does Xanthomonas arboricola pv. pruni affect?", [r"peach|plum|cherry|apricot|Prunus"], [["peach", "plum", "cherry", "apricot", "prunus", "stone fruit"]]),
]
UNANSWERABLE = [
    ("unanswerable_topic", "What exact fungicide dose should I spray on tomato early blight in Telangana?"),
    ("unanswerable_topic", "How many tons of potatoes were lost to late blight in India last year?"),
    ("unanswerable_topic", "What is the price of copper fungicide per litre in Hyderabad?"),
    ("unanswerable_topic", "Which tomato variety grows best in Telangana's climate?"),
    ("unanswerable_topic", "What is the best time of day to spray neem oil on chilli plants?"),
    ("unanswerable_topic", "How much nitrogen fertiliser does an apple tree need each year?"),
    ("unanswerable_topic", "Which pesticide brands has the Indian government approved against citrus greening?"),
    ("unanswerable_topic", "How many days should I wait to harvest grapes after spraying a fungicide?"),
    ("off_topic", "Who won the 2018 football World Cup?"),
    ("off_topic", "How do I reset my home router password?"),
    ("off_topic", "What is the capital city of Australia?"),
    ("off_topic", "How many calories are in a banana?"),
    ("off_topic", "Explain how a transformer neural network works."),
    ("off_topic", "What is a good recipe for chicken biryani?"),
    ("off_topic", "Who is the current Prime Minister of India?"),
]

# Questions whose evidence regex alone matches most of an article also name the section it should be in.
SECTION = {
    "Which two kinds of plants does cedar apple rust need to complete its life cycle?": r"Introduction|Disease cycle",
    "How can tomato yellow leaf curl virus be managed?": r"Management",
    "What humidity levels favour tomato leaf mold?": r"Environment",
    "What cultural practices help control grape black rot?": r"Cultural control|Control",
    "What does gray leaf spot of corn look like?": r"Host and symptoms",
    "What does powdery mildew look like on leaves?": r"Description|Identification",
    "What is crop rotation?": r"Introduction",
    "What are fungicides used for?": r"Introduction",
    "What are the main principles of integrated pest management?": r"Principles|Introduction",
    "How does mulch help plants and soil?": r"Introduction|Uses",
    "What can cause leaf spots on plants?": r"Introduction|Causes|Description",
    "What are rust fungi?": r"Introduction",
}
qs = []
for title, q, must, kw in ANSWERABLE:
    entry = {"type": A, "gold_title": title, "question": q, "must_contain": must, "answer_keywords": kw}
    if q in SECTION:
        entry["gold_section"] = SECTION[q]
    qs.append(entry)
for kind, q in UNANSWERABLE:
    qs.append({"type": kind, "question": q})
# Every third question is the development set (used for any tuning); the rest are the untouched test set.
for i, q in enumerate(qs):
    q["id"] = f"q{i + 1:02d}"
    q["split"] = "dev" if i % 3 == 0 else "test"
json.dump(qs, open("eval/questions.json", "w"), indent=1, ensure_ascii=False)
print(len(qs), "questions:", sum(q["type"] == A for q in qs), "answerable,", sum(q["type"] != A for q in qs), "unanswerable;",
      sum(q["split"] == "dev" for q in qs), "dev /", sum(q["split"] == "test" for q in qs), "test")
