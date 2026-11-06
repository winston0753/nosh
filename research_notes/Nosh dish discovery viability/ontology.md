# Food ontology viability for Nosh

Research checked November 1, 2026. This is a strategy assessment, not an accepted product change. Recommendations below are explicitly inferences, not findings that a particular ontology already produces successful restaurant recommendations.

## Can existing open food knowledge support a dish graph?

### Takeaway
Yes: reuse vocabulary and identifiers, then curate a small consumer-facing layer. Existing resources demonstrate that food knowledge graphs are technically feasible; they do not provide a complete, commercially cleared, personalized catalog of every dish and its real-world availability.

### Cited Findings
- FoodOn is a vocabulary for food materials, products and preparation processes. Its homepage explicitly distinguishes its primary vocabulary goal from a secondary goal of providing commonly referenced food products; it acknowledges that product descriptions are not always highly detailed. The homepage reports over 9,600 generic product categories, which must not be equated with 9,600 restaurant dishes or complete world cuisine coverage. [FoodOn](https://foodon.org/)
- FoodOn's official repository publishes its ontology under CC BY 4.0. This is a useful reusable backbone with attribution obligations, rather than an exclusive Nosh asset. [FoodOn license](https://github.com/FoodOntology/foodon/blob/master/LICENSE.txt)
- Wikidata releases structured data in its main, Property, Lexeme and EntitySchema namespaces under CC0; other namespace text is differently licensed. The licensing page should not be read as a blanket license for linked Wikipedia prose or photographs. [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)
- USDA FoodData Central offers food search and details, public-domain CC0 data and bulk downloads. Its data types include nutrient-oriented Foundation, branded, dietary-survey and legacy records. It is not documented as a live restaurant-menu or dish-availability service. [API guide](https://fdc.nal.usda.gov/api-guide/), [downloads](https://fdc.nal.usda.gov/download-datasets/)
- FoodKG already combines Recipe1M recipes, USDA nutrients and FoodOn ingredient knowledge into linked data. Its build process still requires separately acquiring Recipe1M. This is precedent for the architecture, not proof of production readiness or rights to all inputs. [FoodKG construction](https://foodkg.github.io/foodkg.html)

### Inferences
- The useful Nosh-specific layer is likely an editorial dish vocabulary: multilingual names and aliases; dish families; optional/typical ingredients; preparation; texture; broad sensory dimensions; region/cuisine associations; and provenance. Reuse FoodOn/Wikidata identifiers where they fit, without forcing consumers to navigate their complete scientific hierarchy.
- A limited graph can be more stable and geographically reusable than restaurant business facts. However, describing a dish does not establish who sells it, whether that item is available now, its price, its modifiers, or whether it is deliverable. Dish knowledge and fulfillment knowledge are independent layers.
- A graph-shaped domain model does not require a graph database. A small first version can use ordinary PostgreSQL records and relation tables. This is an engineering recommendation, not a source claim.
- Do not begin with all foods in the world. Start with perhaps 50–150 locally obtainable dish concepts and a bounded set of attributes; this range is a proposed experiment size, not an empirically established optimum. Expand only where requests and observed discovery outcomes justify it.

### Gaps
- No reviewed source establishes comprehensive world-dish coverage, complete sensory profiles, or completeness for a particular Nosh neighborhood. A coverage audit against real local menus is required.
- I have not measured annotation cost or agreement between curators; therefore no dollar or time savings estimate is justified.

## What should the model represent, and can similarity predict liking?

### Takeaway
Separate a dish concept from a particular recipe, menu offer and person's experience. Similarity is a candidate-generation signal; it is not evidence that a user will like the next dish.

### Cited Findings
- FoodOn's design says food-product definitions are still being developed from manually organized categories, with component/process relations supporting richer descriptions. [FoodOn design](https://foodon.org/design/)
- The FoodOn researchers' process-model paper distinguishes ingredients from defining ingredients and describes a recipe prototype with ingredients, devices and process instructions. It notes limits to reasoning and emphasizes appropriate representation. [Food process ontology requirements](https://journals.sagepub.com/doi/10.3233/SW-223096)
- Ahn et al.'s flavor-network study reports different ingredient-compound sharing tendencies across regional cuisines: its Western examples favor sharing while East Asian examples avoid it. This analyzes recipe composition, not individual preference prediction or Nosh conversion. [Original research](https://arxiv.org/abs/1111.6074)
- Recipe1M+ researchers demonstrate joint image/recipe embeddings and semantic retrieval. The evaluated task retrieves a recipe corresponding to an image; it is not a study showing that semantic similarity predicts an individual's enjoyment of an unfamiliar dish. [MIT project](https://im2recipe.csail.mit.edu/)

### Inferences
- Suggested levels: (1) dish concept such as a named noodle dish, (2) a regional or recipe variant, (3) a restaurant's specific menu item and modifiers, (4) an offer at a time and location, (5) the user's response and meal outcome. Combining these levels would wrongly transfer claims about a typical recipe onto a specific order.
- Avoid one-country ownership trees. Represent many-to-many regional/cultural associations, native names, transliterations and variants. Preserve uncertain/disputed relationships instead of inventing authoritative origin claims. This is a modeling recommendation.
- Useful initial features are comprehensible to eaters: brothy versus dry; crisp versus soft; rich versus light; sour/sweet/umami; chili heat; main ingredient; cooking method. Quantities, cooking and ingredient combinations matter, so a list of overlapping ingredients alone is weak.
- Distinguish ontology relations (contains ingredient, variant of) from computed similarity and from behavioral evidence (people who enjoyed X later enjoyed Y). The last can improve only with outcomes; it cannot be manufactured by adding edges to a graph.
- A Yes tap means interest now, not consumption or lasting liking. Keep viewed, interested, chose, ordered/visited, consumed and enjoyed separate. Ask for a light post-meal outcome; optionally ask what the person liked when uncertainty is high. Not today remains timing feedback. Declining one dish must not automatically imply dislike of all its ingredients or country cuisine.
- A possible cross-cuisine recommendation should say what is familiar and what changes, not assert certainty: a shared texture/preparation provides a reason to try, not proof of preference. Treat every proposed bridge as a testable hypothesis.
- Dietary tags need three-valued logic: confirmed compatible, confirmed incompatible, unknown. Generic dish definitions cannot certify a particular vendor's ingredients, preparation, substitutions or cross-contact. Do not infer safe dietary suitability merely from missing ingredient data. This is a product/data-model caution rather than individualized medical advice.
- Evaluate semantic discovery against simpler baselines: curated dish neighbors, explicit user tags, and familiar-cuisine recommendations. If ontology-assisted suggestions do not increase confirmed enjoyment, manageable novelty or repeat use, the added detail has not earned its cost.

### Gaps
- No source reviewed establishes that ingredient/taste graphs alone outperform a modest curated baseline for Nosh's intended users.
- It remains unknown whether users want discovery across cuisines at hungry decision time, versus a familiar low-risk meal. This needs behavioral testing.

## Is the data layer commercially maintainable and defensible?

### Takeaway
A focused, provenance-aware graph is feasible. A globally complete ontology would be a continuing editorial and data-integration operation; open vocabulary by itself is unlikely to be the defensible product asset.

### Cited Findings
- FlavorDB's own FAQ says its ingredient/flavor data was manually compiled from multiple resources and papers, and licenses the work and downloadable data CC BY-NC-SA 3.0. It is not a plug-and-play commercially permissive source for Nosh. [FlavorDB FAQ, questions 15, 19 and 21](https://cosylab.iiitd.edu.in/flavordb/faq)
- Recipe1M+'s project site offers research code/models and describes retrieval research. Its dataset endpoint could not be accessed in this review. MIT DSpace lists CC BY-NC-SA 4.0 for the deposited author manuscript; that is not sufficient evidence to assert the exact separate dataset license. Commercial dataset use must be resolved with its actual terms/rightsholder before adoption. [Project](https://im2recipe.csail.mit.edu/), [MIT publication record](https://dspace.mit.edu/handle/1721.1/130340)
- FoodKG's published construction depends on independently acquired Recipe1M input. The existence of open build code does not itself settle rights to that input. [FoodKG construction](https://foodkg.github.io/foodkg.html)

### Inferences
- Keep source identifier, source URL, license, retrieved version/date, confidence and curator/validation status on imported facts. Keep original claims separate from Nosh's generated interpretations. Do not allow a permissively licensed code repository to be mistaken for rights to bundled/source datasets, images or text.
- LLM-assisted drafting may reduce initial tagging effort, but generated associations need review and evaluation; they are not reliable provenance. Offline editorial tooling could be distinct from the deterministic meal-time ranking path.
- A commercially reusable substrate could combine FoodOn with attribution, Wikidata structured facts, USDA where relevant, and Nosh-authored curated descriptions and observed user feedback. Still audit imported components and the precise intended use.
- The potential moat is not ontology size or semantic search alone. It is a tested mapping from food characteristics to individual positive experiences, coupled to reliable obtainable meals and a habitual user experience. Open-source ontologies make the basic representation available to others too.
- Distinguish a consumer product (help me discover something I will enjoy and can eat) from an ontology/API infrastructure business (sell food normalization/search to other businesses). The latter would need evidence of buyers, integration demand, accuracy and willingness to pay, not merely a consumer reel's appeal.

### Gaps
- Recipe1M commercial terms were not independently confirmed. Do not repeat secondary-site assertions that the manuscript license establishes the dataset license.
- No evidence collected demonstrates willingness to pay for Nosh's ontology as an API or infrastructure product, nor user retention for a dish-first Nosh app.
