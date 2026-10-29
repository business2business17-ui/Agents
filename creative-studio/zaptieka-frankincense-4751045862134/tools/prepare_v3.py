from pathlib import Path
import json
p=Path(__file__).resolve().parents[1]/'v3'
p.mkdir(exist_ok=True)
common='Photorealistic premium skincare lifestyle editorial photography. Pale limestone bathroom, warm neutral ivory cream palette, soft directional morning daylight from upper left, realistic architecture, natural skin texture and anatomically correct hands. Adults only. Models are fictional AI adults, not testimonials. No text, logos, watermark, bottles, packages or soap bars anywhere including reflections: actual product photograph will be composited later. Clear dry frontal stone ledge in foreground for the product. No orange colour cast. '
scenes=[
('02_Hero','Square. Adult woman 35 in ivory bathrobe at sink on left middle ground, gently touching face; mirror and subtle faucet. Empty dry counter lower left. Entire upper and middle right half clean blank ivory wall for typography.'),
('03_Benefits','Square. Adult woman 45 gently patting her cheeks dry with white towel, natural candid expression, on left half near bathroom mirror. Clean dry ledge lower left. Right half blank softly lit ivory wall for text.'),
('04_How_to_use','Square. Close-up natural adult hands covered with a little cleansing foam above a stone sink, action occupies bottom half. Dry ledge bottom right. Upper half softly blurred blank cream bathroom wall for three short instructions. No soap object in hands.'),
('05_Ingredients','Square. Beautiful authentic bathroom vanity with oval ceramic basin far background left, soft towel edge in far background only. Empty flat pale stone countertop across lower half for the only real unwrapped bar later. Right half blank ivory wall. No people needed. No soap dish or fake soap.'),
('06_Size_weight','Square. Dry limestone bathroom shelf in foreground lower right, an adult man 35 wearing a light linen bathrobe softly out of focus in back right by mirror. Left and upper half blank wall for weight and dimensions. Shelf viewed mostly frontally.'),
('07_Ritual','Square. Glass shower enclosure with soft residual steam at rear right, adult woman in fully closed ivory bathrobe with towel around shoulders beside it, relaxed after-shower moment, upper right quadrant. Dry stone vanity in foreground bottom right outside shower. Blank pale wall upper left for text.'),
('B1_Basic_Hero','Landscape. Adult woman in ivory bathrobe near mirror at rear centre, understated natural moment. Dry frontal stone shelf bottom right for packaging. Left 58 percent clean ivory wall for headline. Show clear bathroom context.'),
('B2_Basic_Ritual','Landscape. Closeup adult hands with gentle foam at a ceramic sink on right middle ground, no visible soap. Dry side ledge bottom right. Left 58 percent quiet blank pale wall for steps.'),
('B3_Basic_Ingredients','Landscape. Elegant home bathroom shelf on right foreground, adult woman in white robe softly blurred near mirror on far right background. Dry stone surface. Left 58 percent blank cream wall for ingredient names.'),
('P1_Premium_Hero','Wide panorama. Bright authentic bathroom, adult woman in ivory bathrobe at mirror in right middle ground. Dry stone ledge lower right. Left 60 percent clean pale wall with soft light for large typography.'),
('P2_Premium_Ingredients','Wide panorama. Natural adult woman in robe brushing her hair at bathroom mirror in right background; dry pale limestone counter in right foreground. Left 60 percent empty softly lit ivory wall for ingredient typography.'),
('P3_Premium_Ritual','Wide panorama. Adult man in closed light bathrobe holding a towel after shower, right middle ground, frosted glass shower behind him, natural lived-in refined bathroom. Dry frontal stone shelf lower right, far from water. Left 60 percent pale blank wall for short ritual text.')]
jobs=[{'prompt':common+s,'size':'2048x2048' if i<6 else '2048x1264' if i<9 else '2432x992','quality':'high','out':n+'.png'} for i,(n,s) in enumerate(scenes)]
(p/'generation_jobs.jsonl').write_text('\n'.join(json.dumps(j) for j in jobs),encoding='utf8')
(p/'hero_prompt.txt').write_text(jobs[0]['prompt'],encoding='utf8')
(p/'remaining_jobs.jsonl').write_text('\n'.join(json.dumps(j) for j in jobs[1:]),encoding='utf8')
print('Prepared 12 lifestyle scene prompts')
