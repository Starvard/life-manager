function familyDex() {
 return {
  catalog:[],state:{people:['Ben','Jenna','Rosemary'],counts:{},wishes:{}},person:'Family',query:'',generation:'all',filter:'all',evolutions:false,page:1,loading:true,busy:false,error:'',notice:'',selected:null,timer:null,
  regions:['Kanto · Gen 1','Johto · Gen 2','Hoenn · Gen 3','Sinnoh · Gen 4','Unova · Gen 5','Kalos · Gen 6','Alola · Gen 7','Galar · Gen 8','Paldea · Gen 9'],
  filters:[['all','All Pokémon'],['owned','Owned'],['missing','Missing'],['wish','Wishlist'],['family','Family can help']],
  async init(){try{this.loading=true; const responses=await Promise.all([fetch('/static/data/pokedex.json'),fetch('/api/pokedex',{cache:'no-store'})]);if(responses.some(r=>!r.ok))throw Error();[this.catalog,this.state]=await Promise.all(responses.map(r=>r.json()));this.error='';}catch(e){this.error='Could not load your collection. Please reload.';}finally{this.loading=false;}},
  count(id,who=this.person){if(who==='Family')return this.state.people.reduce((sum,n)=>sum+(this.state.counts[n]?.[id]||0),0);return this.state.counts[who]?.[id]||0;},
  ownedFor(who){return this.catalog.filter(p=>this.count(p.id,who)>0).length;},
  percent(){return this.catalog.length?(100*this.ownedFor(this.person)/this.catalog.length).toFixed(1):'0';},
  isWish(id,who=this.person){return who==='Family'?this.state.people.some(n=>!!this.state.wishes[n]?.[id]):!!this.state.wishes[who]?.[id];},
  helper(id){const owners=this.state.people.filter(n=>this.count(id,n)>0);if(this.person==='Family')return owners.join(' · ')||'Waiting to be found';return !this.count(id)&&owners.length?owners.join(' & ')+' has it':this.count(id)>1?'Extra copy available':this.isWish(id)?'★ On your wishlist':'';},
  get filtered(){let q=this.query.toLowerCase().trim().replace(/^#/,'');return this.catalog.filter(p=>(this.generation==='all'||p.generation===Number(this.generation))&&(!q||p.name.toLowerCase().includes(q)||String(p.id)===String(Number(q)))&&(this.filter==='all'||this.filter==='owned'&&this.count(p.id)>0||this.filter==='missing'&&!this.count(p.id)||this.filter==='wish'&&this.isWish(p.id)||this.filter==='family'&&(this.person==='Family'?this.count(p.id)>0&&this.state.people.some(n=>!this.count(p.id,n)):!this.count(p.id)&&this.count(p.id,'Family')>0))).sort((a,b)=>this.evolutions?a.chain-b.chain||a.id-b.id:a.id-b.id);},
  get groups(){const items=this.filtered.slice((this.page-1)*48,this.page*48);if(!this.evolutions)return[{key:'all',items}];const groups=[];for(const p of items){let g=groups.find(g=>g.key===p.chain);if(!g){const base=this.catalog.find(x=>x.chain===p.chain&&!x.parent);g={key:p.chain,title:(base?.name||p.name)+' family',items:[]};groups.push(g);}g.items.push(p);}return groups;},
  sprite(p){return 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/'+p.sprite+'.png';},
  open(p){this.selected=p;this.$refs.detail.showModal();},
  scrollResults(){document.querySelector('.dex-controls').scrollIntoView({behavior:'smooth',block:'start'});},
  async mutate(payload,message){if(this.busy)return;this.busy=true;this.error='';try{const response=await fetch('/api/pokedex',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const result=await response.json();if(!response.ok)throw Error(result.error||'Save failed.');this.state=result;this.notice=message;clearTimeout(this.timer);this.timer=setTimeout(()=>this.notice='',2600);this.page=Math.min(this.page,Math.max(1,Math.ceil(this.filtered.length/48)));}catch(e){this.error='Your change was not confirmed. Reload before retrying.';}finally{this.busy=false;}},
  change(id,delta,person=this.person){if(person==='Family')return;return this.mutate({person,species:id,action:'count',delta},delta>0?'Card added to '+person+'’s collection':'Card removed from '+person+'’s collection');},
  wish(id,person){return this.mutate({person,species:id,action:'wish',value:!this.isWish(id,person)},'Wishlist updated');}
 };
}
