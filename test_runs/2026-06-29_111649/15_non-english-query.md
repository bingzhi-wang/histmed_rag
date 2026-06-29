# [non-english-query] Multilingual query embedding; filename slug fallback

**Q:** 黄帝内经中关于五脏与季节关系的论述是什么？

- status: ok
- duration: 141.6s
- traditions retrieved: chinese-medicine,greek-medicine,medieval-european
- cited sources: 1,2,6,8,12
- proofread passed: True  | iterations: 2
- trace: logs/2026-06-29_113418_query_25b9c6bd.jsonl
- export: exports/2026-06-29_113418_query_25b9c6bd.md

---

The *Huangdi Neijing Suwen* discusses the relationship between the five zang organs (心, 肺, 脾, 肝, 肾) and the four seasons in two key ways, as outlined in the retrieved passages:  

1. **Seasonal Pathology via Acupuncture Depth (Chapter 50)**:  
   The text explicitly links improper acupuncture depth to seasonal diseases by associating each organ with a specific season. For example:  
   - Injury to the **lung** (肺) causes **autumn illness** (秋病) with symptoms like "warm malaria" (溫瘧) and chills (泝泝然寒慄) [SOURCE 2].  
   - Injury to the **spleen** (脾) leads to **seasonal abdominal distension** (腹脹) recurring every "72 days in the four seasons' months" [SOURCE 2].  
   - Injury to the **heart** (心) causes **summer illness** (夏病) with **heart pain** (心痛) [SOURCE 2].  
   - Injury to the **liver** (肝) results in **spring illness** (春病) with **heat and tendon relaxation** (熱而筋弛) [SOURCE 2].  
   - Injury to the **kidney** (腎) leads to **winter illness** (冬病) with **abdominal distension and waist pain** (脹腰痛) [SOURCE 2].  

   This framework positions each organ as functionally tied to a season, with seasonal pathology arising from disruptions to their physiological integrity.  

2. **Flavor-Season-Organ Correspondence (Chapter 22)**:  
   While not explicitly stating seasonal associations for organs, the text connects **flavors** (五味) to organs and implies a seasonal context through the phrase:  
   > "In accordance with the four seasons (四時) and the five organs (五藏), diseases (病) follow the suitability of the five flavors (五味)" [SOURCE 1].  

   This suggests that dietary therapy (e.g., sour for the heart, bitter for the lungs) must align with seasonal rhythms to prevent disease, though specific seasonal assignments for organs are not detailed here.  

**Comparison with Other Traditions**:  
The retrieved passages from Greek and Latin medical texts (e.g., Hippocratic *Prognostic* or Hildegard von Bingen’s *Causae et Curae*) do not address seasonal-organ relationships in the same way. For instance, Hippocratic medicine focuses on **humoral imbalances** (e.g., phlegm, bile) and environmental factors (e.g., "epidemical diseases" in *Prognostic* [SOURCE 12]), but does not explicitly tie seasons to specific organs. Similarly, Hildegard’s work emphasizes **humoral temperaments** and divine grace in disease, without direct seasonal-organ correlations [SOURCE 6–8].  

Thus, the *Huangdi Neijing* uniquely integrates seasonal-organ pathology through acupuncture and dietary principles, while other traditions prioritize humoral or environmental frameworks without explicit seasonal-organ mappings.


---

**References**

[SOURCE 1] *Huangdi Neijing Suwen (黄帝内经素問)*, Chapter 22 (~300-100 BCE). English translation: LLM-assisted (unreviewed).
    - *Translation:* The color of the heart is red; it should consume sour foods. Small beans (xiǎo dòu), dog meat (quǎn ròu), plums (lǐ), and leeks (jiǔ) are all sour. The color of the lungs is white; it should consume bitter foods. Wheat (mài), mutton (yáng ròu), apricots (xìng), and garlic chives (xiè) are all bitter. The color of the spleen is yellow; it should consume salty foods. Soybeans (dà dòu), pork (shǐ ròu), chestnuts (lì), and hu (huò) are all salty. The color of the kidneys is black; it should consume pungent foods. Yellow millet (huáng shǔ), chicken meat (jī ròu), peaches (táo), and scallions (cōng) […]
    - *Original (zh-classical):* 心色赤，宜食酸，小豆、犬肉、李、韭皆酸。肺色白，宜食苦，麥、羊肉、杏、薤皆苦。脾色黃，宜食鹹，大豆、豕肉、栗、藿皆鹹。腎色黑，宜食辛，黃黍、雞肉、桃、蔥皆辛。辛散，酸收，甘緩，苦堅，鹹耎。毒藥攻邪，五穀為養，五果為助，五畜為益，五菜為充，氣味合而服之，以補精益氣。此五者。有辛酸甘苦鹹，各有所利，或散或收，或緩或急，或堅或耎，四時五藏，病隨五味所宜也。

[SOURCE 2] *Huangdi Neijing Suwen (黄帝内经素問)*, Chapter 50 (~300-100 BCE). English translation: LLM-assisted (unreviewed).
    - *Translation:* Huangdi asked: I wish to hear about the essentials of acupuncture. Qibo replied: Diseases have superficial or deep locations; acupuncture has shallow or deep penetration. Each must reach its proper level, without exceeding its path; exceeding causes internal injury, falling short causes external obstruction, and obstruction allows evil qi to follow. If depth is improperly determined, it becomes a great harm, internally disturbing the five zang-organs and later producing grave illness. Hence it is said: diseases may reside in the hair follicles and skin, in the skin, in the muscles, in the vess […]
    - *Original (zh-classical):* 黃帝問曰：願聞刺要。歧伯對曰：病有浮沈，刺有淺深，各至其理，無過其道；過之則內傷，不及則生外壅，壅則邪從之。淺深不得，反為大賊，內動五藏後生大病。故曰：病有在毫毛腠理者，有在皮膚者，有在肌肉者，有在脈者，有在筋者，有在骨者，有在髓者。是故刺毫毛腠理，無傷皮，皮傷則內動肺，肺動則秋病溫瘧，泝泝然寒慄；刺皮，無傷肉，肉傷則內動脾，脾動則七十二日四季之月，病腹脹煩，不嗜食；刺肉，無傷脈，脈傷則內動心，心動則夏病心痛；刺脈，無傷筋，筋傷則內動肝，肝動則春病熱而筋弛；刺筋無傷骨，骨傷則內動腎，腎動則冬病脹腰痛；刺骨，無傷髓，髓傷則銷鑠，胻酸，體解㑊然不去矣。

[SOURCE 6] Hildegard of Bingen, *Causae et Curae (Hildegard von Bingen), ed. Kaiser 1903*, Passage 206 (~1150-1160 CE). Latin from OCR; English translation: LLM-assisted (unreviewed).
    - *Translation:* Of health. That if the aforementioned humors maintain the correct order and proper measure, as previously stated, in the body, then he is in peace and health of the body; but if they mutually repel one another, they make him weak and infirm, as prescribed. That there are four humors only. From one humor or from two or from three a man cannot consist, but from four, so that they temper one another, as the world consists of four elements, which agree with one another.
    - *Original (la-medieval):* De sanitate. Quod si praedicti humores rectum ordinem sxiiLm et iustam mensuram, ut praefatam est, in bomine servanti ille in quiete et sanitate corporis est; si autem sibi invicem repugnaverint, debilem et infirmum, ut praescriptum est, eum faciunt. Qmd qtiattMr sunt htmores tantum. Ex uno autem bumore aut ex duobus aut ex tribus homo constare non potest, sed ex quatuor, ut invicem temperentur, sicut mundus ex quatuor elementis constat, quae sibi invicem concordant.

[SOURCE 8] Hildegard of Bingen, *Causae et Curae (Hildegard von Bingen), ed. Kaiser 1903*, Passage 573 (~1150-1160 CE). Latin from OCR; English translation: LLM-assisted (unreviewed).
    - *Translation:* When the body senses that, by the grace of God, the tempests of their humors begin to cease, then it understands that it can cast itself free from them, and thus gathers its forces back to itself and expels those humors and lividities from the same body through sweat. And thus that man receives health. But often it happens that the soul, because of excessive heat and cold, cannot fully expel those same humors with sweat, and thus also either joy or sorrow or anger or the affections of that man, struck by fear, withdraws from itself and again remains thus in silence, and sometimes even up to th […]
    - *Original (la-medieval):* Quae dam senserit, quod tempestates humorom illorum per gratiam dei aliqaantam cessare incipiunt, tunc intelligit, quod se de ipsis excutere potest, et ita vires suas ad se do colligit atque homores et livores illos de eodem corpore per sudorem expellit. Et sic homo ille sanitatem recipit. Multotiens antem contingit, quod anima prae nimio ardore et frigore eomndem humorum eos cum sudore pleniter ezpellere non potest, et sic etiam aut laetitia aut tristitia aat ira aat aogastiis hominis illius cum timore concussa se sabtrahit et iterum ita in silentio manet et aliquando 11 etiam usque ad tertia […]

[SOURCE 12] Hippocrates, *Hippocrates, Prognostic (Prognosticon)*, Section 25 (~400 BCE). urn:cts:greekLit:tlg0627.tlg003. Greek text and English translation: Perseus Digital Library.
    - *Translation:* He who would correctly beforehand those that will recover, and those that will die, and in what cases the disease will be protracted for many days, and in what cases for a shorter time, must be able to form a judgment from having made himself acquainted with all the symptoms, and estimating their powers in comparison with one another, as has been described, with regard to the others, and the urine and sputa, as when the patient coughs up pus and bile together. One ought also to consider promptly the influx of epidemical diseases and the constitution of the season. One should likewise be well a […]
    - *Original (grc):* χρὴ δὲ τὸν μέλλοντα ὀρθῶς προγιγνώσκειν τοὺς περιεσομένους καὶ τοὺς ἀποθανουμένους, ὅσοισί τε ἂν μέλλῃ πλέονας ἡμέρας παραμένειν τὸ νούσημα καὶ ὅσοισιν ἂν ἐλάσσους, τὰ σημεῖα ἐκμανθάνοντα πάντα δύνασθαι κρίνειν, λογιζόμενον τὰς δυνάμιας αὐτέων πρὸς ἀλλήλας, ὥσπερ διαγέγραπται περί τε τῶν ἄλλων καὶ τῶν οὔρων καὶ τῶν πτυέλων, ὅταν ὁμοῦ πῦόν τε ἀναβήσσῃ καὶ χολήν. χρὴ δὲ καὶ τὰς φορὰς τῶν νουσημάτων αἰεὶ ἐπιδημεύντων ταχέως ἐνθυμέεσθαι, τήν τε τῆς ὥρης κατάστασιν. εὖ μέντοι χρὴ εἰδέναι περὶ τῶν τεκμηρίων καὶ τῶν ἄλλων σημείων, καὶ μὴ λανθάνειν ὅτι ἐν παντὶ ἔτει καὶ πάση ὥρῃ τά τε κακὰ κακὸν σημαί […]

_7 additional passage(s) retrieved but not cited._

**Proofreading**: All claims are directly supported by the cited sources. The synthesis accurately reflects the content of the *Huangdi Neijing Suwen* passages and correctly notes that Greek/Latin texts do not explicitly map seasons to organs. No anachronisms, over-translation, or missing nuances are detected.
