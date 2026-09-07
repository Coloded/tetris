import {Engine} from '../public/engine.js';
let input='';for await(const c of process.stdin)input+=c;
console.log(JSON.stringify(JSON.parse(input).map(({seed,steps})=>{const e=new Engine(seed);for(const a of steps)e.step(a);return e.export();})));
