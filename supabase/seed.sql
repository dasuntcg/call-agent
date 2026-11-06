-- Business settings for Connecting Brands, drafted from connectingbrands.com.au.
-- Opening hours are an assumption (the website lists none); confirm before go-live.
-- After the first run, edit these in the dashboard Settings page instead.
insert into business_settings (
  business_name,
  greeting,
  services,
  business_hours,
  agent_name,
  timezone,
  service_areas,
  pricing_guidance,
  faqs,
  rules,
  transfer_number,
  transfer_enabled,
  notify_email,
  notify_sms,
  tts_voice_id
) values (
  $s$Connecting Brands$s$,
  $s$Hi, thanks for calling Connecting Brands. You're speaking with Emma, an AI assistant, and this call may be recorded or transcribed. How can I help you today?$s$,
  $s$Fleet branding and signage. Main services: fleet vehicle wraps (full wraps, partial wraps, decals, spot graphics, one-way vision window graphics) for cars, utes, vans, trucks, refrigerated trucks, EVs, construction equipment and boats; truck curtain graphics for curtain-siders; fleet truck painting with custom colour matching; corporate and architectural signage (building signs, illuminated letters, monument signs, wayfinding, safety signage, window prints); digital displays (indoor and outdoor LED screens, video walls, interactive displays with cloud content management); custom large format printing (banners, event and exhibition graphics, window, floor and building wraps, wallpaper); First Nations vehicle wraps with authentic Aboriginal and Torres Strait Islander artwork; and fleet branding that counts toward Reconciliation Action Plan and Indigenous Procurement Policy targets. Also offers in-house design, 3D mockups, project management for national rollouts, and digital services: web design, brand design, app development, digital advertising and AI automation. Works with businesses of every size, from one van to a thousand trucks. 100% First Nations owned and a Supply Nation registered business.$s$,
  $j${"mon": ["08:30", "17:00"], "tue": ["08:30", "17:00"], "wed": ["08:30", "17:00"], "thu": ["08:30", "17:00"], "fri": ["08:30", "17:00"], "sat": null, "sun": null}$j$::jsonb,
  $s$Emma$s$,
  $s$Australia/Sydney$s$,
  $s$Australia-wide through a national network of certified installers, plus New Zealand. Sydney head office at 350 Edgar Street, Condell Park NSW. Brisbane at Unit 1, 31 Warehouse Circuit, Yatala QLD. Albury Wodonga at 1/34 Elkington Road, West Wodonga VIC. Melbourne team servicing Greater Melbourne. Auckland at 47A Victoria Street, Onehunga. Mobile installation at the customer's site is available.$s$,
  $s$You may give these rough ranges, always saying the final price depends on the vehicle, coverage and design and the team will send a detailed quote: partial wraps from about $500 to $1,500, full van wraps about $2,500 to $4,000, large trucks about $4,000 to $8,000. Fleet volume discounts, design-production-install packages, progress payments and finance options are available. Quotes include design, materials, printing and installation, with extras itemised. Do not give prices for signage, digital displays, painting, printing or digital services; those are quoted.$s$,
  $s$How long do wraps last? Usually 5 to 7 years with proper care, up to 10 with premium materials. Premium cast vinyl from 3M, Avery Dennison and Arlon, UV and weather resistant. PVC-free eco options available.
Warranty? Typically 3 to 5 years depending on material, covering material defects, adhesion, premature fading and installation workmanship. Extended options available.
How long does it take? From approval, a single vehicle is typically 5 to 7 business days, a small fleet of 5 to 10 vehicles 2 to 3 weeks, large rollouts are phased. Installation: partial graphics 2 to 4 hours, van or ute full wraps 1 to 2 days, large trucks 2 to 3 days. Express service is available for urgent jobs. Nights and weekends installation can be arranged.
Can you install at our site? Yes, mobile installation needs a clean, covered area out of wind and weather.
Design? In-house designers, first concepts within 48 hours, photorealistic 3D mockups of the actual vehicles, unlimited revisions. Exact brand colour matching. Vector logo files (AI, EPS, PDF) preferred; they can recreate low-resolution logos.
Small businesses? Yes, one vehicle or a whole fleet.
Caring for a wrap? Hand wash with mild soap, touchless car washes are fine, avoid brush washes and pressure washing edges, keep the nozzle 30 centimetres away. Maintenance and repair programs are available.
Who have you worked with? Brands including DHL, Toyota Material Handling, Mainfreight, Bingo Industries, SES, JAX Tyres and Takeuchi.
Email: hello@connectingbrands.com.au. Website: connectingbrands.com.au.$s$,
  $s$Most callers are businesses. As well as the usual details, ask for their business name, which service they're after, how many and what type of vehicles or what signage, where the vehicles are based, and their timeframe. If they have a logo or brand files, say the team will ask for them by email. Auckland and New Zealand enquiries are welcome; take the details the same way.$s$,
  null,
  true,
  null,
  null,
  null
);
