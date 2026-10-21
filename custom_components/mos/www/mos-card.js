function e(e,t,n,i){var o,r=arguments.length,s=r<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,n):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(e,t,n,i);else for(var a=e.length-1;a>=0;a--)(o=e[a])&&(s=(r<3?o(s):r>3?o(t,n,s):o(t,n))||s);return r>3&&s&&Object.defineProperty(t,n,s),s}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,n=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),o=new WeakMap;let r=class{constructor(e,t,n){if(this._$cssResult$=!0,n!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(n&&void 0===e){const n=void 0!==t&&1===t.length;n&&(e=o.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),n&&o.set(t,e))}return e}toString(){return this.cssText}};const s=(e,...t)=>{const n=1===e.length?e[0]:t.reduce((t,n,i)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+e[i+1],e[0]);return new r(n,e,i)},a=n?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const n of e.cssRules)t+=n.cssText;return(e=>new r("string"==typeof e?e:e+"",void 0,i))(t)})(e):e,{is:c,defineProperty:d,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:u,getPrototypeOf:p}=Object,m=globalThis,f=m.trustedTypes,_=f?f.emptyScript:"",g=m.reactiveElementPolyfillSupport,y=(e,t)=>e,b={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let n=e;switch(t){case Boolean:n=null!==e;break;case Number:n=null===e?null:Number(e);break;case Object:case Array:try{n=JSON.parse(e)}catch(e){n=null}}return n}},v=(e,t)=>!c(e,t),w={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:v};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=w){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const n=Symbol(),i=this.getPropertyDescriptor(e,n,t);void 0!==i&&d(this.prototype,e,i)}}static getPropertyDescriptor(e,t,n){const{get:i,set:o}=l(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:i,set(t){const r=i?.call(this);o?.call(this,t),this.requestUpdate(e,r,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??w}static _$Ei(){if(this.hasOwnProperty(y("elementProperties")))return;const e=p(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(y("properties"))){const e=this.properties,t=[...h(e),...u(e)];for(const n of t)this.createProperty(n,e[n])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,n]of t)this.elementProperties.set(e,n)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const n=this._$Eu(e,t);void 0!==n&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const n=new Set(e.flat(1/0).reverse());for(const e of n)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const n=t.attribute;return!1===n?void 0:"string"==typeof n?n:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const n of t.keys())this.hasOwnProperty(n)&&(e.set(n,this[n]),delete this[n]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,i)=>{if(n)e.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const n of i){const i=document.createElement("style"),o=t.litNonce;void 0!==o&&i.setAttribute("nonce",o),i.textContent=n.cssText,e.appendChild(i)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,n){this._$AK(e,n)}_$ET(e,t){const n=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,n);if(void 0!==i&&!0===n.reflect){const o=(void 0!==n.converter?.toAttribute?n.converter:b).toAttribute(t,n.type);this._$Em=e,null==o?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(e,t){const n=this.constructor,i=n._$Eh.get(e);if(void 0!==i&&this._$Em!==i){const e=n.getPropertyOptions(i),o="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:b;this._$Em=i;const r=o.fromAttribute(t,e.type);this[i]=r??this._$Ej?.get(i)??r,this._$Em=null}}requestUpdate(e,t,n,i=!1,o){if(void 0!==e){const r=this.constructor;if(!1===i&&(o=this[e]),n??=r.getPropertyOptions(e),!((n.hasChanged??v)(o,t)||n.useDefault&&n.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,n))))return;this.C(e,t,n)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:n,reflect:i,wrapped:o},r){n&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),!0!==o||void 0!==r)||(this._$AL.has(e)||(this.hasUpdated||n||(t=void 0),this._$AL.set(e,t)),!0===i&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,n]of e){const{wrapped:e}=n,i=this[t];!0!==e||this._$AL.has(t)||void 0===i||this.C(t,void 0,n,i)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[y("elementProperties")]=new Map,$[y("finalized")]=new Map,g?.({ReactiveElement:$}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=e=>e,S=x.trustedTypes,A=S?S.createPolicy("lit-html",{createHTML:e=>e}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+C,P=`<${T}>`,M=document,O=()=>M.createComment(""),U=e=>null===e||"object"!=typeof e&&"function"!=typeof e,N=Array.isArray,z="[ \t\n\f\r]",H=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,L=/-->/g,R=/>/g,j=RegExp(`>|${z}(?:([^\\s"'>=/]+)(${z}*=${z}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),D=/'/g,K=/"/g,I=/^(?:script|style|textarea|title)$/i,W=(e=>(t,...n)=>({_$litType$:e,strings:t,values:n}))(1),B=Symbol.for("lit-noChange"),V=Symbol.for("lit-nothing"),G=new WeakMap,q=M.createTreeWalker(M,129);function Z(e,t){if(!N(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==A?A.createHTML(t):t}const F=(e,t)=>{const n=e.length-1,i=[];let o,r=2===t?"<svg>":3===t?"<math>":"",s=H;for(let t=0;t<n;t++){const n=e[t];let a,c,d=-1,l=0;for(;l<n.length&&(s.lastIndex=l,c=s.exec(n),null!==c);)l=s.lastIndex,s===H?"!--"===c[1]?s=L:void 0!==c[1]?s=R:void 0!==c[2]?(I.test(c[2])&&(o=RegExp("</"+c[2],"g")),s=j):void 0!==c[3]&&(s=j):s===j?">"===c[0]?(s=o??H,d=-1):void 0===c[1]?d=-2:(d=s.lastIndex-c[2].length,a=c[1],s=void 0===c[3]?j:'"'===c[3]?K:D):s===K||s===D?s=j:s===L||s===R?s=H:(s=j,o=void 0);const h=s===j&&e[t+1].startsWith("/>")?" ":"";r+=s===H?n+P:d>=0?(i.push(a),n.slice(0,d)+E+n.slice(d)+C+h):n+C+(-2===d?t:h)}return[Z(e,r+(e[n]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),i]};class X{constructor({strings:e,_$litType$:t},n){let i;this.parts=[];let o=0,r=0;const s=e.length-1,a=this.parts,[c,d]=F(e,t);if(this.el=X.createElement(c,n),q.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(i=q.nextNode())&&a.length<s;){if(1===i.nodeType){if(i.hasAttributes())for(const e of i.getAttributeNames())if(e.endsWith(E)){const t=d[r++],n=i.getAttribute(e).split(C),s=/([.?@])?(.*)/.exec(t);a.push({type:1,index:o,name:s[2],strings:n,ctor:"."===s[1]?te:"?"===s[1]?ne:"@"===s[1]?ie:ee}),i.removeAttribute(e)}else e.startsWith(C)&&(a.push({type:6,index:o}),i.removeAttribute(e));if(I.test(i.tagName)){const e=i.textContent.split(C),t=e.length-1;if(t>0){i.textContent=S?S.emptyScript:"";for(let n=0;n<t;n++)i.append(e[n],O()),q.nextNode(),a.push({type:2,index:++o});i.append(e[t],O())}}}else if(8===i.nodeType)if(i.data===T)a.push({type:2,index:o});else{let e=-1;for(;-1!==(e=i.data.indexOf(C,e+1));)a.push({type:7,index:o}),e+=C.length-1}o++}}static createElement(e,t){const n=M.createElement("template");return n.innerHTML=e,n}}function Y(e,t,n=e,i){if(t===B)return t;let o=void 0!==i?n._$Co?.[i]:n._$Cl;const r=U(t)?void 0:t._$litDirective$;return o?.constructor!==r&&(o?._$AO?.(!1),void 0===r?o=void 0:(o=new r(e),o._$AT(e,n,i)),void 0!==i?(n._$Co??=[])[i]=o:n._$Cl=o),void 0!==o&&(t=Y(e,o._$AS(e,t.values),o,i)),t}class J{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:n}=this._$AD,i=(e?.creationScope??M).importNode(t,!0);q.currentNode=i;let o=q.nextNode(),r=0,s=0,a=n[0];for(;void 0!==a;){if(r===a.index){let t;2===a.type?t=new Q(o,o.nextSibling,this,e):1===a.type?t=new a.ctor(o,a.name,a.strings,this,e):6===a.type&&(t=new oe(o,this,e)),this._$AV.push(t),a=n[++s]}r!==a?.index&&(o=q.nextNode(),r++)}return q.currentNode=M,i}p(e){let t=0;for(const n of this._$AV)void 0!==n&&(void 0!==n.strings?(n._$AI(e,n,t),t+=n.strings.length-2):n._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,n,i){this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=n,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Y(this,e,t),U(e)?e===V||null==e||""===e?(this._$AH!==V&&this._$AR(),this._$AH=V):e!==this._$AH&&e!==B&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>N(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==V&&U(this._$AH)?this._$AA.nextSibling.data=e:this.T(M.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:n}=e,i="number"==typeof n?this._$AC(e):(void 0===n.el&&(n.el=X.createElement(Z(n.h,n.h[0]),this.options)),n);if(this._$AH?._$AD===i)this._$AH.p(t);else{const e=new J(i,this),n=e.u(this.options);e.p(t),this.T(n),this._$AH=e}}_$AC(e){let t=G.get(e.strings);return void 0===t&&G.set(e.strings,t=new X(e)),t}k(e){N(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let n,i=0;for(const o of e)i===t.length?t.push(n=new Q(this.O(O()),this.O(O()),this,this.options)):n=t[i],n._$AI(o),i++;i<t.length&&(this._$AR(n&&n._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,n,i,o){this.type=1,this._$AH=V,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=o,n.length>2||""!==n[0]||""!==n[1]?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=V}_$AI(e,t=this,n,i){const o=this.strings;let r=!1;if(void 0===o)e=Y(this,e,t,0),r=!U(e)||e!==this._$AH&&e!==B,r&&(this._$AH=e);else{const i=e;let s,a;for(e=o[0],s=0;s<o.length-1;s++)a=Y(this,i[n+s],t,s),a===B&&(a=this._$AH[s]),r||=!U(a)||a!==this._$AH[s],a===V?e=V:e!==V&&(e+=(a??"")+o[s+1]),this._$AH[s]=a}r&&!i&&this.j(e)}j(e){e===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===V?void 0:e}}class ne extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==V)}}class ie extends ee{constructor(e,t,n,i,o){super(e,t,n,i,o),this.type=5}_$AI(e,t=this){if((e=Y(this,e,t,0)??V)===B)return;const n=this._$AH,i=e===V&&n!==V||e.capture!==n.capture||e.once!==n.once||e.passive!==n.passive,o=e!==V&&(n===V||i);i&&this.element.removeEventListener(this.name,this,n),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class oe{constructor(e,t,n){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(e){Y(this,e)}}const re=x.litHtmlPolyfillSupport;re?.(X,Q),(x.litHtmlVersions??=[]).push("3.3.2");const se=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let ae=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,n)=>{const i=n?.renderBefore??t;let o=i._$litPart$;if(void 0===o){const e=n?.renderBefore??null;i._$litPart$=o=new Q(t.insertBefore(O(),e),e,void 0,n??{})}return o._$AI(e),o})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return B}};ae._$litElement$=!0,ae.finalized=!0,se.litElementHydrateSupport?.({LitElement:ae});const ce=se.litElementPolyfillSupport;ce?.({LitElement:ae}),(se.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const de={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:v},le=(e=de,t,n)=>{const{kind:i,metadata:o}=n;let r=globalThis.litPropertyMetadata.get(o);if(void 0===r&&globalThis.litPropertyMetadata.set(o,r=new Map),"setter"===i&&((e=Object.create(e)).wrapped=!0),r.set(n.name,e),"accessor"===i){const{name:i}=n;return{set(n){const o=t.get.call(this);t.set.call(this,n),this.requestUpdate(i,o,e,!0,n)},init(t){return void 0!==t&&this.C(i,void 0,e,t),t}}}if("setter"===i){const{name:i}=n;return function(n){const o=this[i];t.call(this,n),this.requestUpdate(i,o,e,!0,n)}}throw Error("Unsupported decorator location: "+i)};function he(e){return(t,n)=>"object"==typeof n?le(e,t,n):((e,t,n)=>{const i=t.hasOwnProperty(n);return t.constructor.createProperty(n,e),i?Object.getOwnPropertyDescriptor(t,n):void 0})(e,t,n)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ue(e){return he({...e,state:!0,attribute:!1})}function pe(e){return e.substr(0,e.indexOf("."))}var me,fe;!function(e){e.language="language",e.system="system",e.comma_decimal="comma_decimal",e.decimal_comma="decimal_comma",e.space_comma="space_comma",e.none="none"}(me||(me={})),function(e){e.language="language",e.system="system",e.am_pm="12",e.twenty_four="24"}(fe||(fe={}));const _e=e=>{if(e.time_format===fe.language||e.time_format===fe.system){const t=e.time_format===fe.language?e.language:void 0,n=(new Date).toLocaleString(t);return n.includes("AM")||n.includes("PM")}return e.time_format===fe.am_pm},ge=e=>new Intl.DateTimeFormat(e.language,{year:"numeric",month:"long",day:"numeric",hour:_e(e)?"numeric":"2-digit",minute:"2-digit",hour12:_e(e)}),ye=e=>new Intl.DateTimeFormat(e.language,{year:"numeric",month:"long",day:"numeric"}),be=e=>new Intl.DateTimeFormat(e.language,{hour:"numeric",minute:"2-digit",hour12:_e(e)});const ve=(e,t,n)=>{const i=t?(e=>{switch(e.number_format){case me.comma_decimal:return["en-US","en"];case me.decimal_comma:return["de","es","it"];case me.space_comma:return["fr","sv","cs"];case me.system:return;default:return e.language}})(t):void 0;if(Number.isNaN=Number.isNaN||function e(t){return"number"==typeof t&&e(t)},(null==t?void 0:t.number_format)!==me.none&&!Number.isNaN(Number(e))&&Intl)try{return new Intl.NumberFormat(i,we(e,n)).format(Number(e))}catch(t){return console.error(t),new Intl.NumberFormat(void 0,we(e,n)).format(Number(e))}return"string"==typeof e?e:`${((e,t=2)=>Math.round(e*Math.pow(10,t))/Math.pow(10,t))(e,null==n?void 0:n.maximumFractionDigits).toString()}${"currency"===(null==n?void 0:n.style)?` ${n.currency}`:""}`},we=(e,t)=>{const n=Object.assign({maximumFractionDigits:2},t);if("string"!=typeof e)return n;if(!t||!t.minimumFractionDigits&&!t.maximumFractionDigits){const t=e.indexOf(".")>-1?e.split(".")[1].length:0;n.minimumFractionDigits=t,n.maximumFractionDigits=t}return n},$e=(e,t,n,i)=>{const o=void 0!==i?i:t.state;if("unknown"===o||"unavailable"===o)return e(`state.default.${o}`);if((e=>!!e.attributes.unit_of_measurement||!!e.attributes.state_class)(t)){if("monetary"===t.attributes.device_class)try{return ve(o,n,{style:"currency",currency:t.attributes.unit_of_measurement})}catch(e){}return`${ve(o,n)}${t.attributes.unit_of_measurement?" "+t.attributes.unit_of_measurement:""}`}const r=function(e){return pe(e.entity_id)}(t);if("input_datetime"===r){let e;return t.attributes.has_date&&t.attributes.has_time?(e=new Date(t.attributes.year,t.attributes.month-1,t.attributes.day,t.attributes.hour,t.attributes.minute),((e,t)=>ge(t).format(e))(e,n)):t.attributes.has_date?(e=new Date(t.attributes.year,t.attributes.month-1,t.attributes.day),((e,t)=>ye(t).format(e))(e,n)):t.attributes.has_time?(e=new Date,e.setHours(t.attributes.hour,t.attributes.minute),((e,t)=>be(t).format(e))(e,n)):t.state}return"humidifier"===r&&"on"===o&&t.attributes.humidity?`${t.attributes.humidity} %`:"counter"===r||"number"===r||"input_number"===r?ve(o,n):t.attributes.device_class&&e(`component.${r}.state.${t.attributes.device_class}.${o}`)||e(`component.${r}.state._.${o}`)||o},xe=["closed","locked","off"],ke=(e,t,n,i)=>{i=i||{},n=null==n?{}:n;const o=new Event(t,{bubbles:void 0===i.bubbles||i.bubbles,cancelable:Boolean(i.cancelable),composed:void 0===i.composed||i.composed});return o.detail=n,e.dispatchEvent(o),o},Se=(e,t)=>{if(e===t)return!0;if(e&&t&&"object"==typeof e&&"object"==typeof t){if(e.constructor!==t.constructor)return!1;let n,i;if(Array.isArray(e)){const o=t;if(i=e.length,i!==o.length)return!1;for(n=i;0!==n--;)if(!Se(e[n],o[n]))return!1;return!0}if(e instanceof Map&&t instanceof Map){if(e.size!==t.size)return!1;for(n of e.entries())if(!t.has(n[0]))return!1;for(n of e.entries())if(!Se(n[1],t.get(n[0])))return!1;return!0}if(e instanceof Set&&t instanceof Set){if(e.size!==t.size)return!1;for(n of e.entries())if(!t.has(n[0]))return!1;return!0}if(ArrayBuffer.isView(e)&&ArrayBuffer.isView(t))return((e,t)=>{if(e.byteLength!==t.byteLength)return!1;const n=new Uint8Array(e.buffer,e.byteOffset,e.byteLength),i=new Uint8Array(t.buffer,t.byteOffset,t.byteLength);for(let e=0;e<n.length;e++)if(n[e]!==i[e])return!1;return!0})(e,t);if(e instanceof RegExp&&t instanceof RegExp)return e.source===t.source&&e.flags===t.flags;if(e.valueOf!==Object.prototype.valueOf)return e.valueOf()===t.valueOf();if(e.toString!==Object.prototype.toString)return e.toString()===t.toString();const o=e,r=t,s=Object.keys(o);if(i=s.length,i!==Object.keys(r).length)return!1;for(n=i;0!==n--;)if(!Object.prototype.hasOwnProperty.call(t,s[n]))return!1;for(n=i;0!==n--;){const e=s[n];if(!Se(o[e],r[e]))return!1}return!0}return e!=e&&t!=t},Ae=e=>{ke(window,"haptic",e)},Ee=(e,t)=>((e,t,n=!0)=>{const i=pe(t),o="group"===i?"homeassistant":i;let r;switch(i){case"lock":r=n?"unlock":"lock";break;case"cover":r=n?"open_cover":"close_cover";break;default:r=n?"turn_on":"turn_off"}return e.callService(o,r,{entity_id:t})})(e,t,xe.includes(e.states[t].state)),Ce=(e,t,n,i)=>{if(i||(i={action:"more-info"}),!i.confirmation||i.confirmation.exemptions&&i.confirmation.exemptions.some(e=>e.user===t.user.id)||(Ae("warning"),confirm(i.confirmation.text||`Are you sure you want to ${i.action}?`)))switch(i.action){case"more-info":(n.entity||n.camera_image)&&ke(e,"hass-more-info",{entityId:n.entity?n.entity:n.camera_image});break;case"navigate":i.navigation_path&&((e,t,n=!1)=>{n?history.replaceState(null,"",t):history.pushState(null,"",t),ke(window,"location-changed",{replace:n})})(0,i.navigation_path);break;case"url":i.url_path&&window.open(i.url_path);break;case"toggle":n.entity&&(Ee(t,n.entity),Ae("success"));break;case"call-service":{if(!i.service)return void Ae("failure");const[e,n]=i.service.split(".",2);t.callService(e,n,i.service_data,i.target),Ae("success");break}case"fire-dom-event":ke(e,"ll-custom",i)}};function Te(e){return void 0!==e&&"none"!==e.action}const Pe=e=>{let t=[];function n(n,i){e=i?n:Object.assign(Object.assign({},e),n);let o=t;for(let t=0;t<o.length;t++)o[t](e)}return{get state(){return e},action(t){function i(e){n(e,!1)}return function(){let n=[e];for(let e=0;e<arguments.length;e++)n.push(arguments[e]);let o=t.apply(this,n);if(null!=o)return o instanceof Promise?o.then(i):i(o)}},setState:n,clearState(){e=void 0},subscribe:e=>(t.push(e),()=>{!function(e){let n=[];for(let i=0;i<t.length;i++)t[i]===e?e=null:n.push(t[i]);t=n}(e)})}},Me=(e,t,n,i,o={unsubGrace:!0})=>{if(e[t])return e[t];let r,s,a=0,c=Pe();const d=()=>{if(!n)throw new Error("Collection does not support refresh");return n(e).then(e=>c.setState(e,!0))},l=()=>d().catch(t=>{if(e.connected)throw t}),h=()=>{s=void 0,r&&r.then(e=>{e()}),c.clearState(),e.removeEventListener("ready",d),e.removeEventListener("disconnected",u)},u=()=>{s&&(clearTimeout(s),h())};return e[t]={get state(){return c.state},refresh:d,subscribe(t){a++,1===a&&(()=>{if(void 0!==s)return clearTimeout(s),void(s=void 0);i&&(r=i(e,c)),n&&(e.addEventListener("ready",l),l()),e.addEventListener("disconnected",u)})();const d=c.subscribe(t);return void 0!==c.state&&setTimeout(()=>t(c.state),0),()=>{d(),a--,a||(o.unsubGrace?s=setTimeout(h,5e3):h())}}},e[t]},Oe=(e,t,n,i,o)=>Me(i,e,t,n).subscribe(o),Ue=["docker_container","compose_stack","lxc_container","virtual_machine","disk","storage_pool","ups"],Ne=new Set(Ue),ze=["name","state"];function He(e){return"string"==typeof e&&Ne.has(e)}const Le=["none","auto","cpu","memory"],Re=e=>{const t={translationKey:`${e}_cpu_usage`,keySuffix:"cpu_usage"},n={translationKey:`${e}_memory_usage`,keySuffix:"memory_usage"};return{cpu:t,memory:n,auto:[t,n]}},je=Re("compose"),De={docker_container:{icon:"mdi:docker",stateTranslationKey:"docker_state",stateKeySuffix:"state",hasPower:!0,updateTranslationKey:"docker_update_available",metrics:Re("docker")},compose_stack:{icon:"mdi:layers",stateTranslationKey:"compose_state",stateKeySuffix:"state",hasPower:!0,updateTranslationKey:"compose_update_available",metrics:{...je,auto:[{translationKey:"compose_running_containers",keySuffix:"running_containers",over:{translationKey:"compose_container_count",keySuffix:"container_count"}},...je.auto]}},lxc_container:{icon:"mdi:linux",stateTranslationKey:"lxc_state",stateKeySuffix:"state",hasPower:!0,metrics:Re("lxc")},virtual_machine:{icon:"mdi:server",stateTranslationKey:"vm_state",stateKeySuffix:"state",hasPower:!0,metrics:Re("vm")},disk:{icon:"mdi:harddisk",stateTranslationKey:"disk_power_status",stateKeySuffix:"power_status",hasPower:!1,metrics:{auto:[{translationKey:"disk_temperature",keySuffix:"temperature"}]}},storage_pool:{icon:"mdi:database",stateTranslationKey:"pool_usage",stateKeySuffix:"usage",hasPower:!1,metrics:{auto:[{translationKey:"pool_free_space",keySuffix:"free_space"}]}},ups:{icon:"mdi:power-plug",stateTranslationKey:"ups_status",stateKeySuffix:"ups_status",hasPower:!1,metrics:{auto:[{translationKey:"ups_load",keySuffix:"ups_load"}]}}},Ke=(e,t)=>Oe("_mosDeviceRegistry",e=>e.sendMessagePromise({type:"config/device_registry/list"}),(e,t)=>e.subscribeEvents(()=>e.sendMessagePromise({type:"config/device_registry/list"}).then(e=>t.setState(e,!0)),"device_registry_updated"),e,t);function Ie(e){const t=new Map(e.map(e=>[e.id,e])),n=new Set;for(const t of e)He(t.model_id)&&t.via_device_id&&n.add(t.via_device_id);return[...n].map(e=>t.get(e)).filter(e=>void 0!==e)}function We(e,t,n){const i=new Set(t);return e.filter(e=>null===e.disabled_by&&He(e.model_id)&&i.has(e.model_id)&&(void 0===n||e.via_device_id===n))}function Be(e){const t=new Map;for(const n of e){if(!n.device_id||null!==n.disabled_by||null!==n.hidden_by)continue;const e=t.get(n.device_id);e?e.push(n):t.set(n.device_id,[n])}return t}function Ve(e,t){const n=De[t];return e.find(e=>e.translation_key===n.stateTranslationKey)??e.find(e=>e.entity_id.startsWith("sensor.")&&e.unique_id?.endsWith(`_${n.stateKeySuffix}`))??e.find(e=>e.entity_id.startsWith("sensor."))}function Ge(e,t){if(De[t].hasPower)return e.find(e=>e.entity_id.startsWith("switch."))}function qe(e,t){const n=De[t].updateTranslationKey;if(n)return e.find(e=>e.translation_key===n)??e.find(e=>e.entity_id.startsWith("binary_sensor.")&&e.unique_id?.endsWith("_update_available"))}const Ze=e=>void 0===e?[]:("string"==typeof e?[e]:e).map(e=>e.trim()).filter(Boolean);function Fe(e,t){const n=e.toLowerCase(),i=t.toLowerCase();if(!i.includes("*")&&!i.includes("?"))return n.includes(i);const o=i.split("").map(e=>"*"===e?".*":"?"===e?".":e.replace(/[.+^${}()|[\]\\]/g,"\\$&")).join("");return new RegExp(`^${o}$`).test(n)}function Xe(e,t){if(!t)return!0;const n=Ze(t.include),i=Ze(t.exclude);return!(n.length&&!n.some(t=>Fe(e,t)))&&!i.some(t=>Fe(e,t))}function Ye(e){return e.filter(e=>e.entity_id.startsWith("binary_sensor."))}function Je(e,t){return e.find(e=>e.translation_key===t.translationKey)??e.find(e=>e.entity_id.startsWith("sensor.")&&e.unique_id?.endsWith(`_${t.keySuffix}`))}function Qe(e,t){const n=[];for(const i of t){const t=Je(e,i);t&&n.push({entity:t,over:i.over?Je(e,i.over):void 0})}return n}const et=[{translationKey:"cpu_load",keySuffix:"cpu_load"},{translationKey:"memory_usage",keySuffix:"memory_usage"},{translationKey:"cpu_temperature",keySuffix:"cpu_temperature"}];function tt(e,t){const n=e.name_by_user||e.name||e.id;if(e.name_by_user)return n;let i=n;t&&i.toLowerCase().startsWith(`${t.toLowerCase()} `)&&(i=i.slice(t.length+1));for(const e of["Docker ","Compose ","LXC ","VM ","Disk ","Pool ","UPS "])if(i.startsWith(e))return i.slice(e.length);return i}function nt(e){return void 0===e||"unavailable"===e||"unknown"===e}var it={version:"Version",invalid_configuration:"Ungültige Konfiguration",loading:"Geräte werden geladen…",no_devices:"Keine MOS-Geräte gefunden",no_state_entity:"Keine Status-Entität",server:"MOS-Server",open_link:"Weboberfläche öffnen",toggle_power:"Starten oder stoppen",power_pending:"Warte auf den Server …",confirm_stop:"{name} wirklich stoppen?",update_available:"Update verfügbar",problem:"Problem gemeldet",show_more:"{count} weitere anzeigen"},ot={kinds_not_a_list:"'kinds' muss eine Liste sein",no_kinds:"'kinds' darf nicht leer sein",unknown_kind:"Unbekannte Geräteart",unknown_sort:"Unbekannte Sortierung",unknown_secondary_info:"Unbekannte Zusatzangabe",bad_max_rows:"'max_rows' muss eine ganze Zahl ab 1 sein",bad_columns:"'columns' muss 1 oder 2 sein"},rt={docker_container:"Docker-Container",compose_stack:"Compose-Stacks",lxc_container:"LXC-Container",virtual_machine:"VMs",disk:"Festplatten",storage_pool:"Speicherpools",ups:"USV"},st={title:"Titel",server:"MOS-Server",all_servers:"Alle Server",kinds:"Gerätearten",kinds_hint:"Wird über die model_id des Geräts gematcht, damit die Liste Containern folgt, die kommen und gehen.",filter_include:"Nur diese Namen",filter_exclude:"Diese Namen ausnehmen",filter_hint:"Komma-getrennt. * und ? sind Platzhalter; ein einfaches Wort passt irgendwo im Namen.",max_rows:"Zeilen je Gruppe",max_rows_hint:"Der Rest klappt hinter einer Zeile zusammen, die ihn öffnet. Leer lassen für kein Limit.",columns:"Spalten",columns_hint:"Zwei ist das Maximum: Home Assistant gibt einer Karte etwa 500 px, das sind zwei lesbare Zeilen nebeneinander — und zwei wollen kompakte Zeilen. Eine schmalere Karte fällt auf eine zurück.",compact:"Kompakte Zeilen",sort:"Sortieren nach",sort_name:"Name",sort_state:"Status, dann Name",secondary_info:"Zusatzwert",secondary_info_hint:"Wird neben dem Status angezeigt. Ein Wert, den der Server gerade nicht liefert, bleibt weg.",secondary_info_none:"Keiner",secondary_info_auto:"Automatisch je Geräteart",secondary_info_cpu:"CPU-Auslastung",secondary_info_memory:"Speicherauslastung",display:"Anzeige",group_by_kind:"Nach Geräteart gruppieren",show_server_summary:"Server-Zusammenfassung anzeigen",show_server_summary_hint:"Zeigt die Auslastung des Servers neben seinem Namen — und diesen Namen auch bei nur einem Server.",show_icon:"Symbol anzeigen",show_state:"Status anzeigen",show_link:"Link anzeigen",show_power:"Start/Stopp-Knopf anzeigen",confirm_stop:"Vor dem Stoppen nachfragen",confirm_stop_hint:"Nur das Stoppen fragt nach. Ein Start ist mit einem zweiten Klick wieder rückgängig.",show_problem:"Problem-Markierung anzeigen",show_problem_hint:"Markiert Geräte, für die die Integration einen Fehler meldet — SMART-Warnung, ungesunder Container, beschädigter Pool.",show_update:"Update-Markierung anzeigen",hide_unavailable:"Nicht verfügbare Geräte ausblenden",actions_note:"Aktionen",tap_action:"Aktion bei Tippen",hold_action:"Aktion bei Gedrückthalten",double_tap_action:"Aktion bei Doppeltippen",actions_hint:"Wird auf die Status-Entität der jeweiligen Zeile angewendet — außer „Umschalten“, das den Start/Stopp-Schalter der Zeile verwendet. Im YAML steht ein Platzhalter wie [[name]] oder [[entity]] an jeder Stelle einer Aktion für die angetippte Zeile."},at={common:it,errors:ot,kinds:rt,editor:st},ct={version:"Version",invalid_configuration:"Invalid configuration",loading:"Loading devices…",no_devices:"No MOS devices found",no_state_entity:"No state entity",server:"MOS server",open_link:"Open web interface",toggle_power:"Start or stop",power_pending:"Waiting for the server…",confirm_stop:"Stop {name}?",update_available:"Update available",problem:"Problem reported",show_more:"Show {count} more"},dt={kinds_not_a_list:"'kinds' must be a list",no_kinds:"'kinds' must not be empty",unknown_kind:"Unknown device kind",unknown_sort:"Unknown sort order",unknown_secondary_info:"Unknown secondary info",bad_max_rows:"'max_rows' must be a whole number of at least 1",bad_columns:"'columns' must be 1 or 2"},lt={docker_container:"Docker containers",compose_stack:"Compose stacks",lxc_container:"LXC containers",virtual_machine:"Virtual machines",disk:"Disks",storage_pool:"Storage pools",ups:"UPS"},ht={title:"Title",server:"MOS server",all_servers:"All servers",kinds:"Device kinds",kinds_hint:"Matched on the device's model_id, so the list follows containers as they come and go.",filter_include:"Only these names",filter_exclude:"Except these names",filter_hint:"Comma-separated. * and ? are wildcards; a plain word matches anywhere in the name.",max_rows:"Rows per group",max_rows_hint:"The rest are folded behind a line that opens them. Leave empty for no limit.",columns:"Columns",columns_hint:"Two is the ceiling: Home Assistant gives a card about 500 px, which is two readable rows across — and two wants compact rows. A narrower card falls back to one.",compact:"Compact rows",sort:"Sort by",sort_name:"Name",sort_state:"State, then name",secondary_info:"Extra value",secondary_info_hint:"Shown beside the state. A value the server cannot report right now is left out.",secondary_info_none:"None",secondary_info_auto:"Automatic per kind",secondary_info_cpu:"CPU usage",secondary_info_memory:"Memory usage",display:"Display",group_by_kind:"Group by kind",show_server_summary:"Show server summary",show_server_summary_hint:"Puts the server's load next to its name, and shows that name even with a single server.",show_icon:"Show icon",show_state:"Show state",show_link:"Show link",show_power:"Show power button",confirm_stop:"Confirm before stopping",confirm_stop_hint:"Only stopping asks. Starting is a second click away from being undone.",show_problem:"Show problem badge",show_problem_hint:"Badges a device the integration reports a fault on — a SMART warning, an unhealthy container, a degraded pool.",show_update:"Show update badge",hide_unavailable:"Hide unavailable devices",actions_note:"Actions",tap_action:"Tap action",hold_action:"Hold action",double_tap_action:"Double tap action",actions_hint:"Applied to each row's own state entity, except Toggle, which uses the row's start/stop switch. In YAML, a placeholder such as [[name]] or [[entity]] anywhere in an action stands for the row that was tapped."},ut={common:ct,errors:dt,kinds:lt,editor:ht};const pt={de:Object.freeze({__proto__:null,common:it,default:at,editor:st,errors:ot,kinds:rt}),en:Object.freeze({__proto__:null,common:ct,default:ut,editor:ht,errors:dt,kinds:lt})},mt="en";let ft;function _t(e){ft=e||void 0}function gt(e,t){const n=e.split(".").reduce((e,t)=>{if(e&&"object"==typeof e&&t in e)return e[t]},t);return"string"==typeof n?n:void 0}function yt(e,t="",n=""){let i;for(const t of function(e){const t=(e??"").replace(/['"]+/g,"").replace("_","-").toLowerCase(),n=t.split("-")[0];return[t,n,mt].filter(Boolean)}(ft??function(){if("undefined"!=typeof localStorage)return localStorage.getItem("selectedLanguage")?.replace(/['"]+/g,"")||void 0}())){const n=pt[t];if(n&&(i=gt(e,n)),void 0!==i)break}return void 0===i&&(i=e),""!==t&&(i=i.replace(t,()=>n)),i}const bt={group_by_kind:!0,sort:"name",secondary_info:"none",show_server_summary:!1,show_icon:!0,show_state:!0,show_link:!0,show_power:!0,confirm_stop:!1,show_problem:!0,columns:1,compact:!1,show_update:!0,hide_unavailable:!1},vt=["group_by_kind","compact","show_server_summary","show_icon","show_state","show_link","show_power","confirm_stop","show_problem","show_update","hide_unavailable"];function wt(e){return void 0===e?"":("string"==typeof e?[e]:e).join(", ")}function $t(e){return String(e??"").split(",").map(e=>e.trim()).filter(Boolean)}const xt=["active","idle","neutral","inactive","unknown"],kt=new Set(["running","on","active","ol","online"]),St=new Set(["paused","frozen","standby","idle","sleeping","starting"]);function At(e,t){if(nt(t))return"unknown";if("disk"===e||"storage_pool"===e)return"neutral";const n=t.toLowerCase();return kt.has(n)?"active":St.has(n)?"idle":"inactive"}const Et=new Set(["http:","https:","homeassistant:"]);function Ct(e,t){return(n,i)=>{if("state"===e){const e=xt.indexOf(At(n.kind,t(n)))-xt.indexOf(At(i.kind,t(i)));if(0!==e)return e}return n.name.localeCompare(i.name)}}function Tt(e,t,n){return void 0===t||n||e.length<=t?{rows:[...e],hidden:0}:{rows:e.slice(0,t),hidden:e.length-t}}class Pt{constructor(e){this.timeoutMs=e,this.timers=new Map}get size(){return this.timers.size}start(e,t){this.stop(e),this.timers.set(e,setTimeout(()=>{this.timers.delete(e),t(e)},this.timeoutMs))}stop(e){const t=this.timers.get(e);void 0!==t&&(clearTimeout(t),this.timers.delete(e))}stopAll(){for(const e of this.timers.values())clearTimeout(e);this.timers.clear()}}const Mt=/\[\[(\w+)\]\]/g;function Ot(e,t){return"string"==typeof e?e.replace(Mt,(e,n)=>Object.hasOwn(t,n)?t[n]??"":e):Array.isArray(e)?e.map(e=>Ot(e,t)):null!==e&&"object"==typeof e?Object.fromEntries(Object.entries(e).map(([e,n])=>[e,Ot(n,t)])):e}function Ut(e,t){if("more-info"===e?.action&&e.entity)return Ot(e.entity,t)||void 0}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class Nt{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,n){this._$Ct=e,this._$AM=t,this._$Ci=n}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}}const zt=(e,t,n)=>{ke(e,t,n)},Ht="ontouchstart"in window||navigator.maxTouchPoints>0||"msMaxTouchPoints"in navigator&&navigator.msMaxTouchPoints>0,Lt=()=>{const e=document.body,t=e.querySelector(".action-handler-mos-card");if(t)return t;const n=document.createElement("div");n.className="action-handler-mos-card",n.style.position="absolute",n.style.width=Ht?"100px":"50px",n.style.height=Ht?"100px":"50px",n.style.transform="translate(-50%, -50%) scale(0)",n.style.pointerEvents="none",n.style.zIndex="999",n.style.transition="transform 0.1s ease-out",n.style.borderRadius="50%",n.style.background="rgba(var(--rgb-primary-color), 0.3)";const i=n;i.holdTime=500,i.cancelled=!1,i.held=!1,i.timer=void 0,i.dblClickTimeout=void 0,i.isRepeating=!1,i.repeatTimeout=void 0,e.appendChild(n);const o=(e=>{const t=e;return t.startAnimation=(e,n)=>{Object.assign(t.style,{left:`${e}px`,top:`${n}px`,transform:"translate(-50%, -50%) scale(1)"})},t.stopAnimation=()=>{Object.assign(t.style,{left:"",top:"",transform:"translate(-50%, -50%) scale(0)"})},t.bind=(e,n={})=>{if(e.actionHandler&&Se(n,e.actionHandler.options))return;if(e.actionHandler?(e.removeEventListener("touchstart",e.actionHandler.start),e.removeEventListener("touchend",e.actionHandler.end),e.removeEventListener("touchcancel",e.actionHandler.end),e.removeEventListener("mousedown",e.actionHandler.start),e.removeEventListener("click",e.actionHandler.end),e.removeEventListener("keydown",e.actionHandler.handleKeyDown),e.actionHandler.handleTouchMove&&e.removeEventListener("touchmove",e.actionHandler.handleTouchMove)):e.addEventListener("contextmenu",e=>{const t=e||window.event;return t.preventDefault&&t.preventDefault(),t.stopPropagation&&t.stopPropagation(),t.cancelBubble=!0,t.returnValue=!1,!1}),e.actionHandler={options:n},n.disabled)return;e.actionHandler.start=i=>{if(i.detail?.ignore)return;let o,r;t.cancelled=!1,t.held=!1,i.touches?(o=i.touches[0].clientX,r=i.touches[0].clientY):(o=i.clientX,r=i.clientY),n.hasHold&&(t.timer=window.setTimeout(()=>{if(t.startAnimation(o,r),t.held=!0,zt(e,"action",{action:"hold"}),n.repeat&&n.repeat>0){let i=0;t.isRepeating=!0,t.repeatTimeout=window.setInterval(()=>{i++,zt(e,"action",{action:"hold"}),n.repeatLimit&&i>=n.repeatLimit&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1)},n.repeat)}},t.holdTime))},e.actionHandler.end=i=>{if(!i.detail?.ignore)return["touchend","touchcancel"].includes(i.type)&&t.cancelled?(t.isRepeating&&t.repeatTimeout&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1),void(n.isMomentary&&zt(e,"action",{action:"release"}))):void("touchcancel"!==i.type&&(["touchend","touchcancel","mouseup"].includes(i.type)&&t.stopAnimation(),t.isRepeating&&t.repeatTimeout&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1),t.timer&&(clearTimeout(t.timer),t.timer=void 0),t.held||(n.hasDoubleClick?"click"===i.type&&i.detail<2||!t.dblClickTimeout?t.dblClickTimeout=window.setTimeout(()=>{t.dblClickTimeout=void 0,zt(e,"action",{action:"tap"})},250):(clearTimeout(t.dblClickTimeout),t.dblClickTimeout=void 0,zt(e,"action",{action:"double_tap"})):zt(e,"action",{action:"tap"})),n.isMomentary&&zt(e,"action",{action:"release"})))},n.disableKbd||(e.actionHandler.handleKeyDown=t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),e.click())});const i=n=>{if(!n.touches)return;const i=n.touches[0],o=e.getBoundingClientRect(),r=i.clientX-o.left,s=i.clientY-o.top;(r<0||s<0||r>=o.width||s>=o.height)&&(t.cancelled=!0)};e.actionHandler.handleTouchMove=i,e.addEventListener("touchstart",e.actionHandler.start,{passive:!0}),e.addEventListener("touchmove",i,{passive:!0}),e.addEventListener("touchend",e.actionHandler.end),e.addEventListener("touchcancel",e.actionHandler.end),e.addEventListener("mousedown",e.actionHandler.start,{passive:!0}),e.addEventListener("click",e.actionHandler.end),n.disableKbd||e.addEventListener("keydown",e.actionHandler.handleKeyDown)},["touchcancel","mouseout","mouseup","touchmove","mousewheel","wheel","scroll"].forEach(e=>{document.addEventListener(e,()=>{t.cancelled=!0,t.timer&&(t.stopAnimation(),clearTimeout(t.timer),t.timer=void 0,t.isRepeating&&t.repeatTimeout&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1))},{passive:!0})}),t})(n);return o};const Rt=(e=>(...t)=>({_$litDirective$:e,values:t}))(class extends Nt{constructor(e){super(e)}render(e){}update(e,[t]){return Se(t,this.previousOptions)||(((e,t)=>{const n=Lt();n&&n.bind(e,t)})(e.element,t),this.previousOptions=t?{...t}:void 0),this.render(t)}});async function jt(e,t,n){return await e().whenDefined("home-assistant"),function(e,t,n){return!e.get(t)&&(e.define(t,n),!0)}(e(),t,n)}console.info(`%c  MOS-CARD \n%c  ${yt("common.version")} 0.3.0    `,"color: orange; font-weight: bold; background: black","color: white; font-weight: bold; background: dimgray");const Dt=window;Dt.customCards=function(e,t){const n=e??[];return n.some(e=>e.type===t.type)||n.push(t),n}(Dt.customCards,{type:"mos-card",name:"MOS NAS Card",description:"Containers, Compose stacks, VMs, disks, pools and the UPS of a MOS NAS server"});class Kt extends ae{constructor(){super(...arguments),this.pending=new Map,this.expanded=new Set,this.pendingTimers=new Pt(2e4),this.unsubscribe=[]}static async getConfigElement(){const{editorDefined:e}=await Promise.resolve().then(function(){return Gt});return await e,document.createElement("mos-card-editor")}static getStubConfig(){return{kinds:[...Ue]}}setConfig(e){this.config=function(e){if(!e)throw new Error(yt("common.invalid_configuration"));if(void 0!==e.kinds){if(!Array.isArray(e.kinds))throw new Error(yt("errors.kinds_not_a_list"));const t=e.kinds.filter(e=>!He(e));if(t.length)throw new Error(`${yt("errors.unknown_kind")}: ${t.join(", ")}`);if(!e.kinds.length)throw new Error(yt("errors.no_kinds"))}if(void 0!==e.sort&&!ze.includes(e.sort))throw new Error(`${yt("errors.unknown_sort")}: ${e.sort}`);if(void 0!==e.secondary_info&&!Le.includes(e.secondary_info))throw new Error(`${yt("errors.unknown_secondary_info")}: ${e.secondary_info}`);if(void 0!==e.max_rows&&(!Number.isInteger(e.max_rows)||e.max_rows<1))throw new Error(`${yt("errors.bad_max_rows")}: ${e.max_rows}`);if(void 0!==e.columns&&(!Number.isInteger(e.columns)||e.columns<1||e.columns>2))throw new Error(`${yt("errors.bad_columns")}: ${e.columns}`);return{kinds:[...Ue],...bt,tap_action:{action:"more-info"},...e}}(e)}connectedCallback(){super.connectedCallback(),this.subscribeRegistries(),this.resumePendingTimers()}disconnectedCallback(){super.disconnectedCallback(),this.unsubscribeRegistries(),this.pendingTimers.stopAll()}willUpdate(e){if(e.has("hass")&&_t(this.hass?.locale?.language),e.has("hass")&&this.pending.size)for(const e of function(e,t){const n=[];for(const[i,o]of e)(t(i)??"")!==o&&n.push(i);return n}(this.pending,e=>this.hass.states[e]?.state))this.clearPending(e)}updated(e){e.has("hass")&&!this.unsubscribe.length&&this.subscribeRegistries()}shouldUpdate(e){if(!this.config)return!1;if(!this.unsubscribe.length&&this.isConnected)return!0;if(e.has("config")||e.has("devices")||e.has("entities")||e.has("icons")||e.has("pending")||e.has("expanded"))return!0;if(!e.has("hass"))return!1;const t=e.get("hass");return!t||(t.locale!==this.hass.locale||t.localize!==this.hass.localize||this.trackedEntityIds().some(e=>t.states[e]!==this.hass.states[e]))}trackedEntityIds(){const e=this.trackedCache;if(e&&e.devices===this.devices&&e.entities===this.entities&&e.config===this.config)return e.ids;const t=[];if(this.devices&&this.entities){const e=this.config.kinds??[...Ue],n=Be(this.entities);for(const i of We(this.devices,e,this.config.server)){const e=n.get(i.id)??[],o=i.model_id,r=Ve(e,o),s=Ge(e,o);r&&t.push(r.entity_id),s&&t.push(s.entity_id);for(const n of this.rowMetrics(e,o))t.push(n.entity.entity_id),n.over&&t.push(n.over.entity_id);if(this.config.show_update){const n=qe(e,o);n&&t.push(n.entity_id)}if(this.config.show_problem)for(const n of Ye(e))t.push(n.entity_id)}if(this.config.show_server_summary)for(const e of Ie(this.devices))for(const i of Qe(n.get(e.id)??[],et))t.push(i.entity.entity_id)}return this.trackedCache={devices:this.devices,entities:this.entities,config:this.config,ids:t},t}subscribeRegistries(){var e,t;!this.unsubscribe.length&&this.isConnected&&this.hass?.connection&&(this.unsubscribe=[Ke(this.hass.connection,e=>{this.devices=e}),(e=this.hass.connection,t=e=>{this.entities=e},Oe("_mosEntityRegistry",e=>e.sendMessagePromise({type:"config/entity_registry/list"}),(e,t)=>e.subscribeEvents(()=>e.sendMessagePromise({type:"config/entity_registry/list"}).then(e=>t.setState(e,!0)),"entity_registry_updated"),e,t))],((e,t)=>e.sendMessagePromise({type:"frontend/get_icons",category:"entity",integration:t}).then(e=>e.resources?.[t]??{}))(this.hass.connection,"mos").then(e=>{this.icons=e}).catch(()=>{}))}unsubscribeRegistries(){for(const e of this.unsubscribe)e();this.unsubscribe=[]}getCardSize(){const e=this.buildSections();if(!e)return 3;const t=e.reduce((e,t)=>e+t.groups.reduce((e,t)=>e+t.rows.length,0),0);return Math.max(3,t+1)}getGridOptions(){return{columns:12,rows:"auto",min_columns:6}}buildSections(){if(!this.devices||!this.entities||!this.config)return;const e=this.config.kinds??[...Ue],t=Be(this.entities),n=this.config.server?this.devices.filter(e=>e.id===this.config.server):Ie(this.devices),i=this.config.server?[]:function(e,t,n){const i=new Set(n);return We(e,t).filter(e=>!i.has(e.via_device_id))}(this.devices,e,n.map(e=>e.id)),o=this.config.server?[this.config.server]:[...n.map(e=>e.id),...i.length?[void 0]:[]],r=[];for(const s of o){const o=n.find(e=>e.id===s),a=o&&(o.name_by_user||o.name)||void 0,c=void 0===s?i:We(this.devices,e,s),d=[];for(const n of e){const e=c.filter(e=>e.model_id===n).map(e=>{const i=t.get(e.id)??[];return{device:e,kind:n,name:tt(e,a),stateEntity:Ve(i,n),powerEntity:Ge(i,n),updateEntity:qe(i,n),metrics:this.rowMetrics(i,n),problemCandidates:this.config.show_problem?Ye(i):[]}}).filter(e=>Xe(e.name,this.config.filter)).filter(e=>!this.config.hide_unavailable||!nt(this.stateValue(e))).sort(Ct(this.config.sort,e=>this.stateValue(e)));if(e.length){const t=`${s??""}:${n}`;d.push({kind:n,key:t,...Tt(e,this.config.max_rows,this.expanded.has(t))})}}d.length&&r.push({server:o,groups:d,serverMetrics:this.config.show_server_summary&&o?Qe(t.get(o.id)??[],et):[]})}return r}stateValue(e){return e.stateEntity?this.hass?.states[e.stateEntity.entity_id]?.state:void 0}rowMetrics(e,t){const n=this.config.secondary_info??"none";return"none"===n?[]:Qe(e,function(e,t){const n=De[e].metrics;if("auto"===t)return n.auto;const i="cpu"===t?n.cpu:"memory"===t?n.memory:void 0;return i?[i]:[]}(t,n))}render(){return W`
      <ha-card .header=${this.config.title}>
        <div class="card-content">${this.renderBody()}</div>
      </ha-card>
    `}renderBody(){const e=this.buildSections();return void 0===e?this.renderNotice(yt("common.loading")):0===e.length?this.renderNotice(yt("common.no_devices")):e.map(t=>this.renderSection(t,e.length>1))}renderNotice(e){return W`<div class="notice">${e}</div>`}renderSection(e,t){const n=e.server&&(e.server.name_by_user||e.server.name)||yt("common.server"),i=this.formatMetrics(e.serverMetrics);return W`
      ${t||i?W`
              <div class="server-heading">
                <span>${n}</span>
                ${i?W`<span class="server-summary">${i}</span>`:V}
              </div>
            `:V}
      ${e.groups.map(e=>this.renderGroup(e))}
    `}renderGroup(e){return W`
      ${this.config.group_by_kind?W`<div class="kind-heading">${yt(`kinds.${e.kind}`)}</div>`:V}
      <div class="group cols-${this.config.columns??1}">${e.rows.map(e=>this.renderRow(e))}</div>
      ${this.renderMore(e)}
    `}renderMore(e){return e.hidden?W`
      <button class="more" @click=${()=>this.expandGroup(e.key)}>
        ${yt("common.show_more","{count}",String(e.hidden))}
      </button>
    `:V}expandGroup(e){this.expanded=new Set(this.expanded).add(e)}renderRow(e){const t=e.stateEntity?this.hass.states[e.stateEntity.entity_id]:void 0,n=nt(t?.state);return W`
      <div
        class="row ${n?"unavailable":""} ${this.config.compact?"compact":""} tone-${At(e.kind,t?.state)}"
      >
        <div
          class="row-body"
          @action=${t=>this.handleAction(t,e)}
          ${Rt({hasHold:Te(this.config.hold_action),hasDoubleClick:Te(this.config.double_tap_action)})}
          tabindex="0"
          role="button"
        >
          ${this.config.show_icon?this.renderIcon(e,t):V}
          <div class="text">
            <span class="name" title=${e.name}>${e.name}</span>
            ${this.renderSecondary(e,t)}
          </div>
        </div>
        ${this.config.show_link?this.renderLink(e,t):V}
        ${this.config.show_power?this.renderPower(e):V}
      </div>
    `}renderIcon(e,t){return W`
      <div class="icon-wrap">
        ${this.renderArtwork(e,t)}${this.renderProblemBadge(e)}${this.renderUpdateBadge(e)}
      </div>
    `}renderProblemBadge(e){if(!this.config.show_problem)return V;const t=e.problemCandidates.map(e=>this.hass.states[e.entity_id]).filter(e=>"problem"===e?.attributes.device_class&&"on"===e.state);if(!t.length)return V;const n=t.map(t=>this.problemName(e,t)).filter(Boolean).join(", ")||yt("common.problem");return W`
      <div class="problem-badge" role="img" aria-label=${n} title=${n}>
        <ha-icon icon="mdi:alert"></ha-icon>
      </div>
    `}problemName(e,t){const n=t.attributes.friendly_name??"",i=e.device.name_by_user||e.device.name||"";return i&&n.startsWith(`${i} `)?n.slice(i.length+1):n}renderArtwork(e,t){const n=t?.attributes.entity_picture;if(n)return W`<img class="icon picture" src=${n} alt="" loading="lazy" />`;const i=t?.attributes.icon||function(e,t,n){if(!e||!t?.translation_key)return;const i=t.entity_id.split(".")[0],o=e[i]?.[t.translation_key];return o?(void 0!==n?o.state?.[n]:void 0)??o.default:void 0}(this.icons,e.stateEntity,t?.state)||De[e.kind].icon;return W`<ha-icon class="icon" .icon=${i}></ha-icon>`}renderUpdateBadge(e){if(!this.config.show_update||!e.updateEntity)return V;if("on"!==this.hass.states[e.updateEntity.entity_id]?.state)return V;const t=yt("common.update_available");return W`
      <div class="update-badge" role="img" aria-label=${t} title=${t}>
        <ha-icon icon="mdi:arrow-up"></ha-icon>
      </div>
    `}renderSecondary(e,t){const n=[];this.config.show_state&&n.push(this.renderState(t));const i=this.formatMetrics(e.metrics);return i&&n.push(i),n.length?W`<span class="state ${i?"with-metrics":""}">${n.join(" · ")}</span>`:V}formatMetrics(e){return e.map(e=>this.formatMetric(e)).filter(e=>void 0!==e).join(" · ")}formatMetric(e){const t=this.hass?.states[e.entity.entity_id];if(!t||nt(t.state))return;const n=this.renderState(t),i=e.over?this.hass?.states[e.over.entity_id]:void 0;return i&&!nt(i.state)?`${n}/${this.renderState(i)}`:n}renderState(e){if(!e)return yt("common.no_state_entity");const t=this.hass;return t.formatEntityState?t.formatEntityState(e):$e(this.hass.localize,e,this.hass.locale)}renderLink(e,t){const n=t?.attributes.web_ui_url||e.device.configuration_url||void 0;return function(e){if(!e)return!1;try{const t=new URL(e);return Et.has(t.protocol)&&""!==t.host}catch{return!1}}(n)?W`
      <a class="link" href=${n} target="_blank" rel="noreferrer noopener" title=${yt("common.open_link")}>
        <ha-icon icon="mdi:web"></ha-icon>
      </a>
    `:V}renderPower(e){if(!e.powerEntity)return V;const t=this.hass.states[e.powerEntity.entity_id];if(!t)return V;const n="on"===t.state,i=this.pending.has(e.powerEntity.entity_id),o=nt(t.state)||i,r=yt(i?"common.power_pending":"common.toggle_power");return W`
      <button
        class="power-button ${i?"pending":""}"
        ?disabled=${o}
        title=${r}
        aria-label=${r}
        @click=${t=>this.togglePower(t,e)}
      >
        ${i?W`<span class="spinner" role="progressbar"></span>`:W`<ha-icon icon=${n?"mdi:stop":"mdi:play"}></ha-icon>`}
      </button>
    `}togglePower(e,t){if(e.stopPropagation(),!t.powerEntity)return;const n=t.powerEntity.entity_id;if(this.pending.has(n))return;const i=this.hass.states[n]?.state,o="on"===i;o&&this.config.confirm_stop&&!confirm(yt("common.confirm_stop","{name}",t.name))||(this.markPending(n,i),this.hass.callService("switch",o?"turn_off":"turn_on",{entity_id:n}).catch(()=>this.clearPending(n)))}markPending(e,t){this.pending=new Map(this.pending).set(e,t??""),this.pendingTimers.start(e,e=>this.clearPending(e))}clearPending(e){if(this.pendingTimers.stop(e),this.pending.has(e)){const t=new Map(this.pending);t.delete(e),this.pending=t}}resumePendingTimers(){for(const e of this.pending.keys())this.pendingTimers.start(e,e=>this.clearPending(e))}configuredAction(e){return"hold"===e?this.config?.hold_action:"double_tap"===e?this.config?.double_tap_action:this.config?.tap_action}handleAction(e,t){if(!this.hass||!this.config||!e.detail?.action)return;const n=this.configuredAction(e.detail.action),i="toggle"===n?.action;if(i&&!t.powerEntity)return;const o=this.placeholderValues(t),r=i?t.powerEntity?.entity_id:t.stateEntity?.entity_id;((e,t,n,i)=>{let o;"double_tap"===i&&n.double_tap_action?o=n.double_tap_action:"hold"===i&&n.hold_action?o=n.hold_action:"tap"===i&&n.tap_action&&(o=n.tap_action),Ce(e,t,n,o)})(this,this.hass,{entity:Ut(n,o)??r,tap_action:Ot(this.config.tap_action,o),hold_action:Ot(this.config.hold_action,o),double_tap_action:Ot(this.config.double_tap_action,o)},e.detail.action)}placeholderValues(e){return{entity:e.stateEntity?.entity_id,power:e.powerEntity?.entity_id,device_id:e.device.id,name:e.name,kind:e.kind}}static get styles(){return s`
      .card-content {
        padding: 4px 12px 12px;
        /* The column layout below asks about the card's own width, not the
           window's: the same card is wide in one dashboard column and narrow in
           three, and only a container query can tell the difference. */
        container-type: inline-size;
      }

      .notice {
        padding: 16px 0;
        color: var(--secondary-text-color);
        text-align: center;
      }

      .server-heading {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        margin: 14px 4px 6px;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      /* Right of the name and quieter than it: the server's load is context for
         the rows below, not a heading of its own. */
      .server-summary {
        flex: 0 1 auto;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.85em;
        font-weight: 400;
        color: var(--secondary-text-color);
      }

      .kind-heading {
        margin: 14px 4px 6px;
        font-size: 0.75em;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--secondary-text-color);
      }

      .group {
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
      }

      .group.cols-2 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      /* A row needs roughly 220px before its name turns to ellipsis, so a card
         too narrow for two of them gets one rather than two unreadable ones. */
      @container (max-width: 440px) {
        .group.cols-2 {
          grid-template-columns: 1fr;
        }
      }

      /* Opens the rows the cap folded away. Sized and coloured like the kind
         headings rather than like a row, so it reads as part of the list's
         furniture and not as another device. */
      .more {
        justify-self: start;
        margin: 8px 4px 0;
        padding: 4px 8px;
        border: none;
        border-radius: 8px;
        background: none;
        cursor: pointer;
        font: inherit;
        font-size: 0.8em;
        font-weight: 500;
        color: var(--secondary-text-color);
      }

      .more:hover {
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 12%, transparent);
      }

      .more:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 1px;
      }

      /* Every row carries a tone class derived from its state; these map it onto
         the theme's own colours, so a custom theme recolours the card without
         the card knowing anything about it. */
      .row {
        --tone-color: var(--secondary-text-color);
        /* Lifted off the card by mixing the text colour into the card's own
           background: a fixed grey would sit invisibly on the card in one theme
           or the other, and this stays a step darker in light and a step lighter
           in dark without needing to know which is in use. Named so the update
           badge can cut its ring out of the same colour. */
        --row-background: color-mix(
          in srgb,
          var(--primary-text-color) 7%,
          var(--ha-card-background, var(--card-background-color))
        );
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        min-height: 56px;
        border-radius: 14px;
        box-sizing: border-box;
        background: var(--row-background);
      }

      /* Everything shrinks together, so the row keeps its proportions and does
         not just look like a squashed version of itself. */
      .row.compact {
        gap: 8px;
        padding: 4px 8px;
        min-height: 40px;
        border-radius: 10px;
      }

      .row.compact .icon {
        width: 32px;
        height: 32px;
        padding: 5px;
        border-radius: 9px;
        --mdc-icon-size: 20px;
      }

      .row.compact .link,
      .row.compact .power-button {
        width: 28px;
        height: 28px;
        --mdc-icon-size: 16px;
      }

      .row.compact .update-badge,
      .row.compact .problem-badge {
        width: 14px;
        height: 14px;
        border-width: 1.5px;
        --mdc-icon-size: 8px;
      }

      .row.compact .spinner {
        width: 13px;
        height: 13px;
      }

      .row.tone-active {
        --tone-color: var(--success-color, var(--state-active-color, #43a047));
      }

      .row.tone-idle {
        --tone-color: var(--warning-color, #ffa726);
      }

      .row.tone-inactive {
        --tone-color: var(--state-inactive-color, var(--secondary-text-color));
      }

      .row.tone-unknown {
        --tone-color: var(--disabled-color, var(--secondary-text-color));
      }

      .row.tone-neutral {
        --tone-color: var(--state-icon-color, var(--secondary-text-color));
      }

      /* The secondary line only takes the tone colour where the tone means
         something; on a neutral row it is ordinary secondary text. */
      .row.tone-neutral .state,
      .row.tone-inactive .state,
      .row.tone-unknown .state {
        color: var(--secondary-text-color);
      }

      .row.unavailable {
        opacity: 0.6;
      }

      .row-body {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 0;
        cursor: pointer;
        border-radius: 10px;
        outline: none;
      }

      .row-body:focus-visible {
        box-shadow: 0 0 0 2px var(--primary-color);
      }

      /* The icon well.
         A rounded square rather than a circle, because most of what lands here
         is a square app logo from the MOS template and a circle clips its
         corners. The tone is carried by a ring around the well instead of a
         wash behind the artwork, which would drain the colour out of it. */
      .icon {
        flex: 0 0 auto;
        width: 44px;
        height: 44px;
        padding: 8px;
        box-sizing: border-box;
        border-radius: 12px;
        color: var(--tone-color);
        background: color-mix(in srgb, var(--tone-color) 16%, transparent);
        --mdc-icon-size: 28px;
      }

      /* The ring is the state signal, so it is only drawn where the state is
         one — otherwise it reads as a stray border around every icon. */
      .row.tone-active .icon,
      .row.tone-idle .icon {
        box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--tone-color) 35%, transparent);
      }

      /* Holds the icon and the badge together. The icon keeps its own box, so
         nothing about its size or spacing changes when no badge is drawn. */
      .icon-wrap {
        position: relative;
        flex: 0 0 auto;
        display: inline-flex;
      }

      .update-badge,
      .problem-badge {
        position: absolute;
        right: -3px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        box-sizing: border-box;
        border-radius: 50%;
        /* The ring is the row's own background, which lifts the badge off the
           icon instead of letting it merge into the corner of a dark logo. */
        border: 2px solid var(--row-background);
        color: var(--text-primary-color, #fff);
        --mdc-icon-size: 10px;
      }

      .update-badge {
        bottom: -3px;
        background: var(--warning-color, #ffa726);
      }

      /* Opposite corner from the update badge, so a container that is both
         unhealthy and out of date shows both without them overlapping. Error
         rather than warning: this one is not a suggestion. */
      .problem-badge {
        top: -3px;
        background: var(--error-color, #db4437);
      }

      /* Artwork gets a neutral well and more room: it brings its own colours,
         and a tinted backdrop behind a logo reads as a stain. */
      .icon.picture {
        padding: 5px;
        object-fit: contain;
        background: color-mix(in srgb, var(--primary-text-color) 6%, transparent);
      }

      .text {
        display: flex;
        flex-direction: column;
        justify-content: center;
        flex: 1;
        min-width: 0;
        gap: 1px;
      }

      .name {
        width: 100%;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-weight: 500;
        line-height: 1.3;
        color: var(--primary-text-color);
      }

      .state {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.85em;
        line-height: 1.3;
        color: var(--tone-color);
      }

      /* A state on its own is a word that can be cut without losing much; a
         measurement cut in half is the one thing the reader asked for and did
         not get. So a line carrying numbers wraps instead, to at most two lines
         — which only happens on a card too narrow to hold them side by side. */
      .state.with-metrics {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        white-space: normal;
      }

      /* Controls sit in matching round wells so the row ends in a consistent
         shape whether a device has a link, a switch, both or neither. */
      .link,
      .power-button {
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        padding: 0;
        border: none;
        border-radius: 50%;
        --mdc-icon-size: 20px;
      }

      .link {
        color: var(--secondary-text-color);
        background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
      }

      .link:hover {
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 18%, transparent);
      }

      .power-button {
        cursor: pointer;
        color: var(--tone-color);
        background: color-mix(in srgb, var(--tone-color) 16%, transparent);
        transition: background 0.15s ease-in-out;
      }

      .power-button:hover {
        background: color-mix(in srgb, var(--tone-color) 30%, transparent);
      }

      .power-button:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 1px;
      }

      .power-button:disabled {
        cursor: default;
        opacity: 0.5;
      }

      /* A waiting button is disabled so it cannot be pressed twice, but it is
         not dimmed like an unavailable one — it is the row's liveliest thing
         at that moment, and fading it says the opposite. */
      .power-button.pending {
        opacity: 1;
      }

      .spinner {
        width: 16px;
        height: 16px;
        box-sizing: border-box;
        border-radius: 50%;
        border: 2px solid color-mix(in srgb, var(--tone-color) 25%, transparent);
        border-top-color: var(--tone-color);
        animation: mos-spin 0.8s linear infinite;
      }

      @keyframes mos-spin {
        to {
          transform: rotate(360deg);
        }
      }

      /* Slowed rather than stopped: a spinner that does not turn says nothing
         at all, which is the one thing this element exists to avoid. */
      @media (prefers-reduced-motion: reduce) {
        .spinner {
          animation-duration: 2.4s;
        }
      }
    `}}e([he({attribute:!1})],Kt.prototype,"hass",void 0),e([ue()],Kt.prototype,"config",void 0),e([ue()],Kt.prototype,"devices",void 0),e([ue()],Kt.prototype,"entities",void 0),e([ue()],Kt.prototype,"icons",void 0),e([ue()],Kt.prototype,"pending",void 0),e([ue()],Kt.prototype,"expanded",void 0),jt(()=>customElements,"mos-card",Kt);const It=[{name:"tap_action",default:"more-info"},{name:"hold_action",default:"none"},{name:"double_tap_action",default:"none"}],Wt={kinds:"editor.kinds_hint",confirm_stop:"editor.confirm_stop_hint",secondary_info:"editor.secondary_info_hint",show_server_summary:"editor.show_server_summary_hint",show_problem:"editor.show_problem_hint",filter_include:"editor.filter_hint",max_rows:"editor.max_rows_hint",columns:"editor.columns_hint"};class Bt extends ae{constructor(){super(...arguments),this._servers=[],this._computeLabel=e=>yt(`editor.${e.name}`),this._computeHelper=e=>{const t=Wt[e.name];return t?yt(t):""}}setConfig(e){this._config=e}connectedCallback(){super.connectedCallback(),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.(),this._unsubscribe=void 0}willUpdate(e){e.has("hass")&&_t(this.hass?.locale?.language)}updated(e){e.has("hass")&&this._subscribe()}_subscribe(){!this._unsubscribe&&this.isConnected&&this.hass?.connection&&(this._unsubscribe=Ke(this.hass.connection,e=>{this._servers=Ie(e)}))}_schema(){return[{name:"title",selector:{text:{}}},{name:"server",selector:{select:{mode:"dropdown",options:[{value:"",label:yt("editor.all_servers")},...this._servers.map(e=>({value:e.id,label:e.name_by_user||e.name||e.id}))]}}},{name:"kinds",selector:{select:{multiple:!0,options:Ue.map(e=>({value:e,label:yt(`kinds.${e}`)}))}}},{name:"filter_include",selector:{text:{}}},{name:"filter_exclude",selector:{text:{}}},{name:"max_rows",selector:{number:{min:1,max:100,mode:"box"}}},{name:"columns",selector:{number:{min:1,max:2,mode:"slider"}}},{name:"sort",selector:{select:{mode:"dropdown",options:ze.map(e=>({value:e,label:yt(`editor.sort_${e}`)}))}}},{name:"secondary_info",selector:{select:{mode:"dropdown",options:Le.map(e=>({value:e,label:yt(`editor.secondary_info_${e}`)}))}}},...vt.map(e=>({name:e,selector:{boolean:{}}})),{name:"actions_note",type:"constant",value:yt("editor.actions_hint")},...It.map(e=>({name:e.name,selector:{ui_action:{default_action:e.default}}}))]}_data(e){const t={title:e.title??"",server:e.server??"",kinds:e.kinds??[...Ue],sort:e.sort??bt.sort,secondary_info:e.secondary_info??bt.secondary_info,columns:e.columns??bt.columns,filter_include:wt(e.filter?.include),filter_exclude:wt(e.filter?.exclude),max_rows:e.max_rows};for(const n of vt){const i=e[n];t[n]="boolean"==typeof i?i:bt[n]}for(const n of It)t[n.name]=e[n.name];return t}render(){return this._config&&this.hass?W`
      <ha-form
        .hass=${this.hass}
        .data=${this._data(this._config)}
        .schema=${this._schema()}
        .computeLabel=${this._computeLabel}
        .computeHelper=${this._computeHelper}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `:V}_valueChanged(e){if(!this._config)return;const t=e.detail.value,n={...this._config,...t},i=function(e,t){const n=$t(e),i=$t(t);if(n.length||i.length)return{...n.length?{include:n}:{},...i.length?{exclude:i}:{}}}(t.filter_include,t.filter_exclude);delete n.filter_include,delete n.filter_exclude,i?n.filter=i:delete n.filter,t.max_rows||delete n.max_rows,Array.isArray(t.kinds)&&!t.kinds.length&&delete n.kinds,t.title||delete n.title,t.server||delete n.server;for(const e of It)t[e.name]||delete n[e.name];ke(this,"config-changed",{config:n})}static get styles(){return s`
      ha-form {
        display: block;
      }
    `}}e([he({attribute:!1})],Bt.prototype,"hass",void 0),e([ue()],Bt.prototype,"_config",void 0),e([ue()],Bt.prototype,"_servers",void 0);const Vt=jt(()=>customElements,"mos-card-editor",Bt);var Gt=Object.freeze({__proto__:null,MosCardEditor:Bt,editorDefined:Vt});export{Kt as MosCard};
