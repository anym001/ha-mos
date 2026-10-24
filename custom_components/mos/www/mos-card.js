function e(e,t,i,n){var s,o=arguments.length,r=o<3?t:null===n?n=Object.getOwnPropertyDescriptor(t,i):n;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)r=Reflect.decorate(e,t,i,n);else for(var a=e.length-1;a>=0;a--)(s=e[a])&&(r=(o<3?s(r):o>3?s(t,i,r):s(t,i))||r);return o>3&&r&&Object.defineProperty(t,i,r),r}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,n=Symbol(),s=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==n)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=s.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&s.set(t,e))}return e}toString(){return this.cssText}};const r=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,n)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[n+1],e[0]);return new o(i,e,n)},a=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,n))(t)})(e):e,{is:c,defineProperty:l,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:u,getPrototypeOf:p}=Object,m=globalThis,f=m.trustedTypes,g=f?f.emptyScript:"",_=m.reactiveElementPolyfillSupport,v=(e,t)=>e,y={toAttribute(e,t){switch(t){case Boolean:e=e?g:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},b=(e,t)=>!c(e,t),w={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:b};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=w){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),n=this.getPropertyDescriptor(e,i,t);void 0!==n&&l(this.prototype,e,n)}}static getPropertyDescriptor(e,t,i){const{get:n,set:s}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:n,set(t){const o=n?.call(this);s?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??w}static _$Ei(){if(this.hasOwnProperty(v("elementProperties")))return;const e=p(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(v("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(v("properties"))){const e=this.properties,t=[...h(e),...u(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,n)=>{if(i)e.adoptedStyleSheets=n.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of n){const n=document.createElement("style"),s=t.litNonce;void 0!==s&&n.setAttribute("nonce",s),n.textContent=i.cssText,e.appendChild(n)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,i);if(void 0!==n&&!0===i.reflect){const s=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(t,i.type);this._$Em=e,null==s?this.removeAttribute(n):this.setAttribute(n,s),this._$Em=null}}_$AK(e,t){const i=this.constructor,n=i._$Eh.get(e);if(void 0!==n&&this._$Em!==n){const e=i.getPropertyOptions(n),s="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:y;this._$Em=n;const o=s.fromAttribute(t,e.type);this[n]=o??this._$Ej?.get(n)??o,this._$Em=null}}requestUpdate(e,t,i,n=!1,s){if(void 0!==e){const o=this.constructor;if(!1===n&&(s=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??b)(s,t)||i.useDefault&&i.reflect&&s===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:n,wrapped:s},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==s||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===n&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,n=this[t];!0!==e||this._$AL.has(t)||void 0===n||this.C(t,void 0,i,n)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[v("elementProperties")]=new Map,x[v("finalized")]=new Map,_?.({ReactiveElement:x}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const $=globalThis,k=e=>e,S=$.trustedTypes,A=S?S.createPolicy("lit-html",{createHTML:e=>e}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,M="?"+C,T=`<${M}>`,P=document,O=()=>P.createComment(""),z=e=>null===e||"object"!=typeof e&&"function"!=typeof e,L=Array.isArray,N="[ \t\n\f\r]",U=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,H=/>/g,D=RegExp(`>|${N}(?:([^\\s"'>=/]+)(${N}*=${N}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),j=/'/g,K=/"/g,B=/^(?:script|style|textarea|title)$/i,I=e=>(t,...i)=>({_$litType$:e,strings:t,values:i}),F=I(1),G=I(2),W=Symbol.for("lit-noChange"),V=Symbol.for("lit-nothing"),q=new WeakMap,Z=P.createTreeWalker(P,129);function Y(e,t){if(!L(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==A?A.createHTML(t):t}const X=(e,t)=>{const i=e.length-1,n=[];let s,o=2===t?"<svg>":3===t?"<math>":"",r=U;for(let t=0;t<i;t++){const i=e[t];let a,c,l=-1,d=0;for(;d<i.length&&(r.lastIndex=d,c=r.exec(i),null!==c);)d=r.lastIndex,r===U?"!--"===c[1]?r=R:void 0!==c[1]?r=H:void 0!==c[2]?(B.test(c[2])&&(s=RegExp("</"+c[2],"g")),r=D):void 0!==c[3]&&(r=D):r===D?">"===c[0]?(r=s??U,l=-1):void 0===c[1]?l=-2:(l=r.lastIndex-c[2].length,a=c[1],r=void 0===c[3]?D:'"'===c[3]?K:j):r===K||r===j?r=D:r===R||r===H?r=U:(r=D,s=void 0);const h=r===D&&e[t+1].startsWith("/>")?" ":"";o+=r===U?i+T:l>=0?(n.push(a),i.slice(0,l)+E+i.slice(l)+C+h):i+C+(-2===l?t:h)}return[Y(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),n]};class J{constructor({strings:e,_$litType$:t},i){let n;this.parts=[];let s=0,o=0;const r=e.length-1,a=this.parts,[c,l]=X(e,t);if(this.el=J.createElement(c,i),Z.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(n=Z.nextNode())&&a.length<r;){if(1===n.nodeType){if(n.hasAttributes())for(const e of n.getAttributeNames())if(e.endsWith(E)){const t=l[o++],i=n.getAttribute(e).split(C),r=/([.?@])?(.*)/.exec(t);a.push({type:1,index:s,name:r[2],strings:i,ctor:"."===r[1]?ne:"?"===r[1]?se:"@"===r[1]?oe:ie}),n.removeAttribute(e)}else e.startsWith(C)&&(a.push({type:6,index:s}),n.removeAttribute(e));if(B.test(n.tagName)){const e=n.textContent.split(C),t=e.length-1;if(t>0){n.textContent=S?S.emptyScript:"";for(let i=0;i<t;i++)n.append(e[i],O()),Z.nextNode(),a.push({type:2,index:++s});n.append(e[t],O())}}}else if(8===n.nodeType)if(n.data===M)a.push({type:2,index:s});else{let e=-1;for(;-1!==(e=n.data.indexOf(C,e+1));)a.push({type:7,index:s}),e+=C.length-1}s++}}static createElement(e,t){const i=P.createElement("template");return i.innerHTML=e,i}}function Q(e,t,i=e,n){if(t===W)return t;let s=void 0!==n?i._$Co?.[n]:i._$Cl;const o=z(t)?void 0:t._$litDirective$;return s?.constructor!==o&&(s?._$AO?.(!1),void 0===o?s=void 0:(s=new o(e),s._$AT(e,i,n)),void 0!==n?(i._$Co??=[])[n]=s:i._$Cl=s),void 0!==s&&(t=Q(e,s._$AS(e,t.values),s,n)),t}class ee{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,n=(e?.creationScope??P).importNode(t,!0);Z.currentNode=n;let s=Z.nextNode(),o=0,r=0,a=i[0];for(;void 0!==a;){if(o===a.index){let t;2===a.type?t=new te(s,s.nextSibling,this,e):1===a.type?t=new a.ctor(s,a.name,a.strings,this,e):6===a.type&&(t=new re(s,this,e)),this._$AV.push(t),a=i[++r]}o!==a?.index&&(s=Z.nextNode(),o++)}return Z.currentNode=P,n}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class te{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,n){this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Q(this,e,t),z(e)?e===V||null==e||""===e?(this._$AH!==V&&this._$AR(),this._$AH=V):e!==this._$AH&&e!==W&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>L(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==V&&z(this._$AH)?this._$AA.nextSibling.data=e:this.T(P.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,n="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=J.createElement(Y(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(t);else{const e=new ee(n,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=q.get(e.strings);return void 0===t&&q.set(e.strings,t=new J(e)),t}k(e){L(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,n=0;for(const s of e)n===t.length?t.push(i=new te(this.O(O()),this.O(O()),this,this.options)):i=t[n],i._$AI(s),n++;n<t.length&&(this._$AR(i&&i._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ie{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,n,s){this.type=1,this._$AH=V,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=s,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=V}_$AI(e,t=this,i,n){const s=this.strings;let o=!1;if(void 0===s)e=Q(this,e,t,0),o=!z(e)||e!==this._$AH&&e!==W,o&&(this._$AH=e);else{const n=e;let r,a;for(e=s[0],r=0;r<s.length-1;r++)a=Q(this,n[i+r],t,r),a===W&&(a=this._$AH[r]),o||=!z(a)||a!==this._$AH[r],a===V?e=V:e!==V&&(e+=(a??"")+s[r+1]),this._$AH[r]=a}o&&!n&&this.j(e)}j(e){e===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ne extends ie{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===V?void 0:e}}class se extends ie{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==V)}}class oe extends ie{constructor(e,t,i,n,s){super(e,t,i,n,s),this.type=5}_$AI(e,t=this){if((e=Q(this,e,t,0)??V)===W)return;const i=this._$AH,n=e===V&&i!==V||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,s=e!==V&&(i===V||n);n&&this.element.removeEventListener(this.name,this,i),s&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class re{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){Q(this,e)}}const ae=$.litHtmlPolyfillSupport;ae?.(J,te),($.litHtmlVersions??=[]).push("3.3.2");const ce=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let le=class extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const n=i?.renderBefore??t;let s=n._$litPart$;if(void 0===s){const e=i?.renderBefore??null;n._$litPart$=s=new te(t.insertBefore(O(),e),e,void 0,i??{})}return s._$AI(e),s})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}};le._$litElement$=!0,le.finalized=!0,ce.litElementHydrateSupport?.({LitElement:le});const de=ce.litElementPolyfillSupport;de?.({LitElement:le}),(ce.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const he={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:b},ue=(e=he,t,i)=>{const{kind:n,metadata:s}=i;let o=globalThis.litPropertyMetadata.get(s);if(void 0===o&&globalThis.litPropertyMetadata.set(s,o=new Map),"setter"===n&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===n){const{name:n}=i;return{set(i){const s=t.get.call(this);t.set.call(this,i),this.requestUpdate(n,s,e,!0,i)},init(t){return void 0!==t&&this.C(n,void 0,e,t),t}}}if("setter"===n){const{name:n}=i;return function(i){const s=this[n];t.call(this,i),this.requestUpdate(n,s,e,!0,i)}}throw Error("Unsupported decorator location: "+n)};function pe(e){return(t,i)=>"object"==typeof i?ue(e,t,i):((e,t,i)=>{const n=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),n?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function me(e){return pe({...e,state:!0,attribute:!1})}function fe(e){return e.substr(0,e.indexOf("."))}var ge,_e;!function(e){e.language="language",e.system="system",e.comma_decimal="comma_decimal",e.decimal_comma="decimal_comma",e.space_comma="space_comma",e.none="none"}(ge||(ge={})),function(e){e.language="language",e.system="system",e.am_pm="12",e.twenty_four="24"}(_e||(_e={}));const ve=e=>{if(e.time_format===_e.language||e.time_format===_e.system){const t=e.time_format===_e.language?e.language:void 0,i=(new Date).toLocaleString(t);return i.includes("AM")||i.includes("PM")}return e.time_format===_e.am_pm},ye=e=>new Intl.DateTimeFormat(e.language,{year:"numeric",month:"long",day:"numeric",hour:ve(e)?"numeric":"2-digit",minute:"2-digit",hour12:ve(e)}),be=e=>new Intl.DateTimeFormat(e.language,{year:"numeric",month:"long",day:"numeric"}),we=e=>new Intl.DateTimeFormat(e.language,{hour:"numeric",minute:"2-digit",hour12:ve(e)});const xe=(e,t,i)=>{const n=t?(e=>{switch(e.number_format){case ge.comma_decimal:return["en-US","en"];case ge.decimal_comma:return["de","es","it"];case ge.space_comma:return["fr","sv","cs"];case ge.system:return;default:return e.language}})(t):void 0;if(Number.isNaN=Number.isNaN||function e(t){return"number"==typeof t&&e(t)},(null==t?void 0:t.number_format)!==ge.none&&!Number.isNaN(Number(e))&&Intl)try{return new Intl.NumberFormat(n,$e(e,i)).format(Number(e))}catch(t){return console.error(t),new Intl.NumberFormat(void 0,$e(e,i)).format(Number(e))}return"string"==typeof e?e:`${((e,t=2)=>Math.round(e*Math.pow(10,t))/Math.pow(10,t))(e,null==i?void 0:i.maximumFractionDigits).toString()}${"currency"===(null==i?void 0:i.style)?` ${i.currency}`:""}`},$e=(e,t)=>{const i=Object.assign({maximumFractionDigits:2},t);if("string"!=typeof e)return i;if(!t||!t.minimumFractionDigits&&!t.maximumFractionDigits){const t=e.indexOf(".")>-1?e.split(".")[1].length:0;i.minimumFractionDigits=t,i.maximumFractionDigits=t}return i},ke=(e,t,i,n)=>{const s=void 0!==n?n:t.state;if("unknown"===s||"unavailable"===s)return e(`state.default.${s}`);if((e=>!!e.attributes.unit_of_measurement||!!e.attributes.state_class)(t)){if("monetary"===t.attributes.device_class)try{return xe(s,i,{style:"currency",currency:t.attributes.unit_of_measurement})}catch(e){}return`${xe(s,i)}${t.attributes.unit_of_measurement?" "+t.attributes.unit_of_measurement:""}`}const o=function(e){return fe(e.entity_id)}(t);if("input_datetime"===o){let e;return t.attributes.has_date&&t.attributes.has_time?(e=new Date(t.attributes.year,t.attributes.month-1,t.attributes.day,t.attributes.hour,t.attributes.minute),((e,t)=>ye(t).format(e))(e,i)):t.attributes.has_date?(e=new Date(t.attributes.year,t.attributes.month-1,t.attributes.day),((e,t)=>be(t).format(e))(e,i)):t.attributes.has_time?(e=new Date,e.setHours(t.attributes.hour,t.attributes.minute),((e,t)=>we(t).format(e))(e,i)):t.state}return"humidifier"===o&&"on"===s&&t.attributes.humidity?`${t.attributes.humidity} %`:"counter"===o||"number"===o||"input_number"===o?xe(s,i):t.attributes.device_class&&e(`component.${o}.state.${t.attributes.device_class}.${s}`)||e(`component.${o}.state._.${s}`)||s},Se=["closed","locked","off"],Ae=(e,t,i,n)=>{n=n||{},i=null==i?{}:i;const s=new Event(t,{bubbles:void 0===n.bubbles||n.bubbles,cancelable:Boolean(n.cancelable),composed:void 0===n.composed||n.composed});return s.detail=i,e.dispatchEvent(s),s},Ee=(e,t)=>{if(e===t)return!0;if(e&&t&&"object"==typeof e&&"object"==typeof t){if(e.constructor!==t.constructor)return!1;let i,n;if(Array.isArray(e)){const s=t;if(n=e.length,n!==s.length)return!1;for(i=n;0!==i--;)if(!Ee(e[i],s[i]))return!1;return!0}if(e instanceof Map&&t instanceof Map){if(e.size!==t.size)return!1;for(i of e.entries())if(!t.has(i[0]))return!1;for(i of e.entries())if(!Ee(i[1],t.get(i[0])))return!1;return!0}if(e instanceof Set&&t instanceof Set){if(e.size!==t.size)return!1;for(i of e.entries())if(!t.has(i[0]))return!1;return!0}if(ArrayBuffer.isView(e)&&ArrayBuffer.isView(t))return((e,t)=>{if(e.byteLength!==t.byteLength)return!1;const i=new Uint8Array(e.buffer,e.byteOffset,e.byteLength),n=new Uint8Array(t.buffer,t.byteOffset,t.byteLength);for(let e=0;e<i.length;e++)if(i[e]!==n[e])return!1;return!0})(e,t);if(e instanceof RegExp&&t instanceof RegExp)return e.source===t.source&&e.flags===t.flags;if(e.valueOf!==Object.prototype.valueOf)return e.valueOf()===t.valueOf();if(e.toString!==Object.prototype.toString)return e.toString()===t.toString();const s=e,o=t,r=Object.keys(s);if(n=r.length,n!==Object.keys(o).length)return!1;for(i=n;0!==i--;)if(!Object.prototype.hasOwnProperty.call(t,r[i]))return!1;for(i=n;0!==i--;){const e=r[i];if(!Ee(s[e],o[e]))return!1}return!0}return e!=e&&t!=t},Ce=e=>{Ae(window,"haptic",e)},Me=(e,t)=>((e,t,i=!0)=>{const n=fe(t),s="group"===n?"homeassistant":n;let o;switch(n){case"lock":o=i?"unlock":"lock";break;case"cover":o=i?"open_cover":"close_cover";break;default:o=i?"turn_on":"turn_off"}return e.callService(s,o,{entity_id:t})})(e,t,Se.includes(e.states[t].state)),Te=(e,t,i,n)=>{if(n||(n={action:"more-info"}),!n.confirmation||n.confirmation.exemptions&&n.confirmation.exemptions.some(e=>e.user===t.user.id)||(Ce("warning"),confirm(n.confirmation.text||`Are you sure you want to ${n.action}?`)))switch(n.action){case"more-info":(i.entity||i.camera_image)&&Ae(e,"hass-more-info",{entityId:i.entity?i.entity:i.camera_image});break;case"navigate":n.navigation_path&&((e,t,i=!1)=>{i?history.replaceState(null,"",t):history.pushState(null,"",t),Ae(window,"location-changed",{replace:i})})(0,n.navigation_path);break;case"url":n.url_path&&window.open(n.url_path);break;case"toggle":i.entity&&(Me(t,i.entity),Ce("success"));break;case"call-service":{if(!n.service)return void Ce("failure");const[e,i]=n.service.split(".",2);t.callService(e,i,n.service_data,n.target),Ce("success");break}case"fire-dom-event":Ae(e,"ll-custom",n)}},Pe=(e,t,i,n)=>{let s;"double_tap"===n&&i.double_tap_action?s=i.double_tap_action:"hold"===n&&i.hold_action?s=i.hold_action:"tap"===n&&i.tap_action&&(s=i.tap_action),Te(e,t,i,s)};function Oe(e){return void 0!==e&&"none"!==e.action}const ze=e=>{let t=[];function i(i,n){e=n?i:Object.assign(Object.assign({},e),i);let s=t;for(let t=0;t<s.length;t++)s[t](e)}return{get state(){return e},action(t){function n(e){i(e,!1)}return function(){let i=[e];for(let e=0;e<arguments.length;e++)i.push(arguments[e]);let s=t.apply(this,i);if(null!=s)return s instanceof Promise?s.then(n):n(s)}},setState:i,clearState(){e=void 0},subscribe:e=>(t.push(e),()=>{!function(e){let i=[];for(let n=0;n<t.length;n++)t[n]===e?e=null:i.push(t[n]);t=i}(e)})}},Le=(e,t,i,n,s={unsubGrace:!0})=>{if(e[t])return e[t];let o,r,a=0,c=ze();const l=()=>{if(!i)throw new Error("Collection does not support refresh");return i(e).then(e=>c.setState(e,!0))},d=()=>l().catch(t=>{if(e.connected)throw t}),h=()=>{r=void 0,o&&o.then(e=>{e()}),c.clearState(),e.removeEventListener("ready",l),e.removeEventListener("disconnected",u)},u=()=>{r&&(clearTimeout(r),h())};return e[t]={get state(){return c.state},refresh:l,subscribe(t){a++,1===a&&(()=>{if(void 0!==r)return clearTimeout(r),void(r=void 0);n&&(o=n(e,c)),i&&(e.addEventListener("ready",d),d()),e.addEventListener("disconnected",u)})();const l=c.subscribe(t);return void 0!==c.state&&setTimeout(()=>t(c.state),0),()=>{l(),a--,a||(s.unsubGrace?r=setTimeout(h,5e3):h())}}},e[t]},Ne=(e,t,i,n,s)=>Le(n,e,t,i).subscribe(s),Ue=["docker_container","compose_stack","lxc_container","virtual_machine","disk","storage_pool","ups"],Re=new Set(Ue),He=["name","state"];function De(e){return"string"==typeof e&&Re.has(e)}const je=["none","auto","cpu","memory"],Ke=e=>{const t={translationKey:`${e}_cpu_usage`,keySuffix:"cpu_usage",label:"cpu",icon:"mdi:speedometer"},i={translationKey:`${e}_memory_usage`,keySuffix:"memory_usage",label:"memory",icon:"mdi:memory"};return{cpu:t,memory:i,auto:[t,i]}},Be=Ke("compose"),Ie={docker_container:{icon:"mdi:docker",stateTranslationKey:"docker_state",stateKeySuffix:"state",hasPower:!0,updateTranslationKey:"docker_update_available",metrics:Ke("docker")},compose_stack:{icon:"mdi:layers",stateTranslationKey:"compose_state",stateKeySuffix:"state",hasPower:!0,updateTranslationKey:"compose_update_available",metrics:{...Be,auto:[{translationKey:"compose_running_containers",keySuffix:"running_containers",label:"containers",icon:"mdi:package-variant-closed",over:{translationKey:"compose_container_count",keySuffix:"container_count",label:"containers",icon:"mdi:package-variant-closed"}},...Be.auto]}},lxc_container:{icon:"mdi:linux",stateTranslationKey:"lxc_state",stateKeySuffix:"state",hasPower:!0,metrics:Ke("lxc")},virtual_machine:{icon:"mdi:server",stateTranslationKey:"vm_state",stateKeySuffix:"state",hasPower:!0,metrics:Ke("vm")},disk:{icon:"mdi:harddisk",stateTranslationKey:"disk_power_status",stateKeySuffix:"power_status",hasPower:!1,metrics:{auto:[{translationKey:"disk_usage",keySuffix:"usage",label:"used",icon:"mdi:harddisk"},{translationKey:"disk_temperature",keySuffix:"temperature",label:"temperature",icon:"mdi:thermometer"}]},activities:[{translationKey:"disk_preclear_running",keySuffix:"preclear_running",label:"preclear",icon:"mdi:autorenew"}]},storage_pool:{icon:"mdi:database",stateTranslationKey:"pool_usage",stateKeySuffix:"usage",hasPower:!1,metrics:{auto:[{translationKey:"pool_free_space",keySuffix:"free_space",label:"free",icon:"mdi:database-outline",over:{translationKey:"pool_total_space",keySuffix:"total_space",label:"total",icon:"mdi:database"}}]},activities:[{translationKey:"pool_scrub_running",keySuffix:"scrub_running",label:"scrub",icon:"mdi:autorenew"},{translationKey:"pool_balance_running",keySuffix:"balance_running",label:"balance",icon:"mdi:autorenew"},{translationKey:"pool_parity_running",keySuffix:"parity_running",label:"parity",icon:"mdi:autorenew"}]},ups:{icon:"mdi:power-plug",stateTranslationKey:"ups_status",stateKeySuffix:"ups_status",hasPower:!1,metrics:{auto:[{translationKey:"ups_battery_charge",keySuffix:"ups_battery_charge",label:"battery",icon:"mdi:battery",inverse:!0},{translationKey:"ups_battery_runtime",keySuffix:"ups_battery_runtime",label:"runtime",icon:"mdi:timer-outline"},{translationKey:"ups_load",keySuffix:"ups_load",label:"load",icon:"mdi:gauge"}]}}},Fe=(e,t)=>Ne("_mosDeviceRegistry",e=>e.sendMessagePromise({type:"config/device_registry/list"}),(e,t)=>e.subscribeEvents(()=>e.sendMessagePromise({type:"config/device_registry/list"}).then(e=>t.setState(e,!0)),"device_registry_updated"),e,t),Ge=(e,t)=>Ne("_mosEntityRegistry",e=>e.sendMessagePromise({type:"config/entity_registry/list"}),(e,t)=>e.subscribeEvents(()=>e.sendMessagePromise({type:"config/entity_registry/list"}).then(e=>t.setState(e,!0)),"entity_registry_updated"),e,t);function We(e){const t=new Map(e.map(e=>[e.id,e])),i=new Set;for(const t of e)De(t.model_id)&&t.via_device_id&&i.add(t.via_device_id);return[...i].map(e=>t.get(e)).filter(e=>void 0!==e)}function Ve(e,t,i){const n=new Set(t);return e.filter(e=>null===e.disabled_by&&De(e.model_id)&&n.has(e.model_id)&&(void 0===i||e.via_device_id===i))}function qe(e){const t=new Map;for(const i of e){if(!i.device_id||null!==i.disabled_by||null!==i.hidden_by)continue;const e=t.get(i.device_id);e?e.push(i):t.set(i.device_id,[i])}return t}function Ze(e,t){const i=Ie[t];return e.find(e=>e.translation_key===i.stateTranslationKey)??e.find(e=>e.entity_id.startsWith("sensor.")&&e.unique_id?.endsWith(`_${i.stateKeySuffix}`))??e.find(e=>e.entity_id.startsWith("sensor."))}function Ye(e,t){if(Ie[t].hasPower)return e.find(e=>e.entity_id.startsWith("switch."))}function Xe(e,t){const i=Ie[t].updateTranslationKey;if(i)return e.find(e=>e.translation_key===i)??e.find(e=>e.entity_id.startsWith("binary_sensor.")&&e.unique_id?.endsWith("_update_available"))}const Je=e=>void 0===e?[]:("string"==typeof e?[e]:e).map(e=>e.trim()).filter(Boolean);function Qe(e,t){const i=e.toLowerCase(),n=t.toLowerCase();if(!n.includes("*")&&!n.includes("?"))return i.includes(n);const s=n.split("").map(e=>"*"===e?".*":"?"===e?".":e.replace(/[.+^${}()|[\]\\]/g,"\\$&")).join("");return new RegExp(`^${s}$`).test(i)}function et(e,t){if(!t)return!0;const i=Je(t.include),n=Je(t.exclude);return!(i.length&&!i.some(t=>Qe(e,t)))&&!n.some(t=>Qe(e,t))}function tt(e){return e.filter(e=>e.entity_id.startsWith("binary_sensor."))}function it(e,t,i="sensor"){return e.find(e=>e.translation_key===t.translationKey)??e.find(e=>e.entity_id.startsWith(`${i}.`)&&e.unique_id?.endsWith(`_${t.keySuffix}`))}function nt(e,t){return(Ie[t].activities??[]).flatMap(t=>{const i=it(e,t,"binary_sensor");return i?[{ref:t,entity:i}]:[]})}function st(e,t){const i=[];for(const n of t){const t=it(e,n);t&&i.push({ref:n,entity:t,over:n.over?it(e,n.over):void 0})}return i}function ot(e,t){const i=Ie[e].metrics;if("auto"===t)return i.auto;const n="cpu"===t?i.cpu:"memory"===t?i.memory:void 0;return n?[n]:[]}const rt=[{translationKey:"cpu_load",keySuffix:"cpu_load",icon:"mdi:speedometer",label:"cpu",gauge:!0},{translationKey:"memory_usage",keySuffix:"memory_usage",icon:"mdi:memory",label:"memory",gauge:!0},{translationKey:"cpu_temperature",keySuffix:"cpu_temperature",icon:"mdi:thermometer",label:"temperature",gauge:!1}],at={translationKey:"boot_time",keySuffix:"boot_time",icon:"mdi:clock-outline"},ct=[{translationKey:"ssh_enabled",keySuffix:"ssh_enabled",label:"service",icon:"mdi:console",name:"SSH"},{translationKey:"samba_enabled",keySuffix:"samba_enabled",label:"service",icon:"mdi:folder-network",name:"Samba"},{translationKey:"nfs_enabled",keySuffix:"nfs_enabled",label:"service",icon:"mdi:folder-network-outline",name:"NFS"},{translationKey:"tailscale_online",keySuffix:"tailscale_online",label:"service",icon:"mdi:vpn",name:"Tailscale"},{translationKey:"netbird_online",keySuffix:"netbird_online",label:"service",icon:"mdi:vpn",name:"NetBird"}];function lt(e){return ct.flatMap(t=>{const i=it(e,t,"binary_sensor");return i?[{ref:t,entity:i}]:[]})}function dt(e,t){const i=e.name_by_user||e.name||e.id;if(e.name_by_user)return i;let n=i;t&&n.toLowerCase().startsWith(`${t.toLowerCase()} `)&&(n=n.slice(t.length+1));for(const e of["Docker ","Compose ","LXC ","VM ","Disk ","Pool ","UPS "])if(n.startsWith(e))return n.slice(e.length);return n}function ht(e){return void 0===e||"unavailable"===e||"unknown"===e}var ut={invalid_configuration:"Ungültige Konfiguration",loading:"Geräte werden geladen…",no_devices:"Keine MOS-Geräte gefunden",no_state_entity:"Keine Status-Entität",server:"MOS-Server",open_link:"Weboberfläche öffnen",toggle_power:"Starten oder stoppen",power_pending:"Warte auf den Server …",confirm_stop:"{name} wirklich stoppen?",update_available:"Update verfügbar",problem:"Problem gemeldet",show_more:"{count} weitere anzeigen"},pt={kinds_not_a_list:"'kinds' muss eine Liste sein",no_kinds:"'kinds' darf nicht leer sein",unknown_kind:"Unbekannte Geräteart",unknown_sort:"Unbekannte Sortierung",unknown_secondary_info:"Unbekannte Zusatzangabe",bad_max_rows:"'max_rows' muss eine ganze Zahl ab 1 sein",bad_columns:"'columns' muss 1 oder 2 sein",not_a_boolean:"Muss true oder false sein",not_a_string:"Muss Text sein"},mt={docker_container:"Docker-Container",compose_stack:"Compose-Stacks",lxc_container:"LXC-Container",virtual_machine:"VMs",disk:"Festplatten",storage_pool:"Speicherpools",ups:"USV"},ft={title:"Titel",server:"MOS-Server",all_servers:"Alle Server",kinds:"Gerätearten",kinds_hint:"Wird über die model_id des Geräts gematcht, damit die Liste Containern folgt, die kommen und gehen.",filter_include:"Nur diese Namen",filter_exclude:"Diese Namen ausnehmen",filter_hint:"Komma-getrennt. * und ? sind Platzhalter; ein einfaches Wort passt irgendwo im Namen.",max_rows:"Zeilen je Gruppe",max_rows_hint:"Der Rest klappt hinter einer Zeile zusammen, die ihn öffnet. Leer lassen für kein Limit.",columns:"Spalten",columns_hint:"Zwei ist das Maximum: Home Assistant gibt einer Karte etwa 500 px, das sind zwei lesbare Zeilen nebeneinander — und zwei wollen kompakte Zeilen. Eine schmalere Karte fällt auf eine zurück.",compact:"Kompakte Zeilen",sort:"Sortieren nach",sort_name:"Name",sort_state:"Status, dann Name",secondary_info:"Zusatzwert",secondary_info_hint:"Wird neben dem Status angezeigt. Ein Wert, den der Server gerade nicht liefert, bleibt weg.",secondary_info_none:"Keiner",secondary_info_auto:"Automatisch je Geräteart",secondary_info_cpu:"CPU-Auslastung",secondary_info_memory:"Speicherauslastung",display:"Anzeige",group_by_kind:"Nach Geräteart gruppieren",show_server_summary:"Server-Zusammenfassung anzeigen",show_server_summary_hint:"Zeigt Auslastung, Arbeitsspeicher und Temperatur des Servers unter seinem Namen — und diesen Namen auch bei nur einem Server.",show_history:"Lastverlauf anzeigen",show_history_hint:"Zeigt die letzte Stunde von CPU-Last und Arbeitsspeicher neben den Ringen des Servers. Braucht die Server-Zusammenfassung und den Recorder von Home Assistant.",show_services:"Dienste anzeigen",show_services_hint:"SSH, Samba, NFS, Tailscale und NetBird als Chips unter der Server-Zusammenfassung, hervorgehoben solange aktiv.",show_icon:"Symbol anzeigen",show_state:"Status anzeigen",show_link:"Link anzeigen",show_power:"Start/Stopp-Knopf anzeigen",confirm_stop:"Vor dem Stoppen nachfragen",confirm_stop_hint:"Nur das Stoppen fragt nach. Ein Start ist mit einem zweiten Klick wieder rückgängig.",show_problem:"Problem-Markierung anzeigen",show_problem_hint:"Markiert Geräte, für die die Integration einen Fehler meldet — SMART-Warnung, ungesunder Container, beschädigter Pool.",show_update:"Update-Markierung anzeigen",hide_unavailable:"Nicht verfügbare Geräte ausblenden",actions_note:"Aktionen",tap_action:"Aktion bei Tippen",hold_action:"Aktion bei Gedrückthalten",double_tap_action:"Aktion bei Doppeltippen",actions_hint:"Wird auf die Status-Entität der jeweiligen Zeile angewendet — außer „Umschalten“, das den Start/Stopp-Schalter der Zeile verwendet. Im YAML steht ein Platzhalter wie [[name]] oder [[entity]] an jeder Stelle einer Aktion für die angetippte Zeile."},gt={cpu:"CPU",memory:"RAM",temperature:"Temp.",containers:"Container",free:"Frei",load:"Last",used:"Belegt",battery:"Akku",runtime:"Laufzeit",total:"Gesamt",uptime:"Laufzeit",uptime_for:"Läuft seit {duration}",service:"Dienst",scrub:"Scrub",balance:"Balance",parity:"Paritätsprüfung",preclear:"Preclear"},_t={running:"{running}/{total} laufen",update:"{count} Update",updates:"{count} Updates"},vt={d:"T",h:"Std.",min:"Min."},yt={OL:"Netzbetrieb",OB:"Akkubetrieb",LB:"Akku schwach",HB:"Akku hoch",RB:"Akku tauschen",CHRG:"Lädt",DISCHRG:"Entlädt",BYPASS:"Bypass",CAL:"Kalibriert",OFF:"Aus",OVER:"Überlast",TRIM:"Spannung gesenkt",BOOST:"Spannung angehoben",FSD:"Zwangsabschaltung"},bt={guests:"Gäste",storage:"Speicher",power:"Strom",running:"laufen",disks:"{count} Festplatten",standby:"{count} im Standby",max:"max.",problems:"{count} mit Fehler",free:"frei",free_of_total:"Frei von gesamt"},wt={title:"Titel",server:"MOS-Server",show_history:"Lastverlauf anzeigen",show_guests:"Gäste anzeigen",show_storage:"Speicher anzeigen",show_ups:"USV anzeigen",show_services:"Dienste anzeigen",navigation_path:"Tippen auf eine Gast-Art öffnet",navigation_path_hint:"Ein Dashboard-Pfad, zum Beispiel /mos/container. [[kind]] wird durch die Art ersetzt, etwa docker_container. Leer lassen für kein Tippen."},xt={common:ut,errors:pt,kinds:mt,editor:ft,metrics:gt,counts:_t,units:vt,ups:yt,overview:bt,overview_editor:wt},$t={invalid_configuration:"Invalid configuration",loading:"Loading devices…",no_devices:"No MOS devices found",no_state_entity:"No state entity",server:"MOS server",open_link:"Open web interface",toggle_power:"Start or stop",power_pending:"Waiting for the server…",confirm_stop:"Stop {name}?",update_available:"Update available",problem:"Problem reported",show_more:"Show {count} more"},kt={kinds_not_a_list:"'kinds' must be a list",no_kinds:"'kinds' must not be empty",unknown_kind:"Unknown device kind",unknown_sort:"Unknown sort order",unknown_secondary_info:"Unknown secondary info",bad_max_rows:"'max_rows' must be a whole number of at least 1",bad_columns:"'columns' must be 1 or 2",not_a_boolean:"Must be true or false",not_a_string:"Must be text"},St={docker_container:"Docker containers",compose_stack:"Compose stacks",lxc_container:"LXC containers",virtual_machine:"Virtual machines",disk:"Disks",storage_pool:"Storage pools",ups:"UPS"},At={title:"Title",server:"MOS server",all_servers:"All servers",kinds:"Device kinds",kinds_hint:"Matched on the device's model_id, so the list follows containers as they come and go.",filter_include:"Only these names",filter_exclude:"Except these names",filter_hint:"Comma-separated. * and ? are wildcards; a plain word matches anywhere in the name.",max_rows:"Rows per group",max_rows_hint:"The rest are folded behind a line that opens them. Leave empty for no limit.",columns:"Columns",columns_hint:"Two is the ceiling: Home Assistant gives a card about 500 px, which is two readable rows across — and two wants compact rows. A narrower card falls back to one.",compact:"Compact rows",sort:"Sort by",sort_name:"Name",sort_state:"State, then name",secondary_info:"Extra value",secondary_info_hint:"Shown beside the state. A value the server cannot report right now is left out.",secondary_info_none:"None",secondary_info_auto:"Automatic per kind",secondary_info_cpu:"CPU usage",secondary_info_memory:"Memory usage",display:"Display",group_by_kind:"Group by kind",show_server_summary:"Show server summary",show_server_summary_hint:"Shows the server's load, memory and temperature under its name, and that name even with a single server.",show_history:"Show load history",show_history_hint:"Draws the last hour of CPU load and memory usage beside the server's rings. Needs the server summary and Home Assistant's recorder.",show_services:"Show services",show_services_hint:"SSH, Samba, NFS, Tailscale and NetBird as chips under the server summary, lit while on.",show_icon:"Show icon",show_state:"Show state",show_link:"Show link",show_power:"Show power button",confirm_stop:"Confirm before stopping",confirm_stop_hint:"Only stopping asks. Starting is a second click away from being undone.",show_problem:"Show problem badge",show_problem_hint:"Badges a device the integration reports a fault on — a SMART warning, an unhealthy container, a degraded pool.",show_update:"Show update badge",hide_unavailable:"Hide unavailable devices",actions_note:"Actions",tap_action:"Tap action",hold_action:"Hold action",double_tap_action:"Double tap action",actions_hint:"Applied to each row's own state entity, except Toggle, which uses the row's start/stop switch. In YAML, a placeholder such as [[name]] or [[entity]] anywhere in an action stands for the row that was tapped."},Et={cpu:"CPU",memory:"Memory",temperature:"Temp",containers:"Containers",free:"Free",load:"Load",used:"Used",battery:"Battery",runtime:"Runtime",total:"Total",uptime:"Uptime",uptime_for:"Up {duration}",service:"Service",scrub:"Scrub",balance:"Balance",parity:"Parity check",preclear:"Preclear"},Ct={running:"{running}/{total} running",update:"{count} update",updates:"{count} updates"},Mt={d:"d",h:"h",min:"min"},Tt={OL:"Online",OB:"On battery",LB:"Battery low",HB:"Battery high",RB:"Replace battery",CHRG:"Charging",DISCHRG:"Discharging",BYPASS:"Bypass",CAL:"Calibrating",OFF:"Off",OVER:"Overload",TRIM:"Trimming voltage",BOOST:"Boosting voltage",FSD:"Forced shutdown"},Pt={guests:"Guests",storage:"Storage",power:"Power",running:"running",disks:"{count} disks",standby:"{count} in standby",max:"max",problems:"{count} with a fault",free:"free",free_of_total:"Free of total"},Ot={title:"Title",server:"MOS server",show_history:"Show load history",show_guests:"Show guests",show_storage:"Show storage",show_ups:"Show UPS",show_services:"Show services",navigation_path:"Tap on a guest kind opens",navigation_path_hint:"A dashboard path, for example /mos/containers. [[kind]] becomes the kind, e.g. docker_container. Leave empty for no tap."},zt={common:$t,errors:kt,kinds:St,editor:At,metrics:Et,counts:Ct,units:Mt,ups:Tt,overview:Pt,overview_editor:Ot};const Lt={de:Object.freeze({__proto__:null,common:ut,counts:_t,default:xt,editor:ft,errors:pt,kinds:mt,metrics:gt,overview:bt,overview_editor:wt,units:vt,ups:yt}),en:Object.freeze({__proto__:null,common:$t,counts:Ct,default:zt,editor:At,errors:kt,kinds:St,metrics:Et,overview:Pt,overview_editor:Ot,units:Mt,ups:Tt})},Nt="en";let Ut;function Rt(e){Ut=e||void 0}function Ht(e,t){const i=e.split(".").reduce((e,t)=>{if(e&&"object"==typeof e&&t in e)return e[t]},t);return"string"==typeof i?i:void 0}function Dt(e,t="",i=""){let n;for(const t of function(e){const t=(e??"").replace(/['"]+/g,"").replace("_","-").toLowerCase(),i=t.split("-")[0];return[t,i,Nt].filter(Boolean)}(Ut??function(){if("undefined"!=typeof localStorage)return localStorage.getItem("selectedLanguage")?.replace(/['"]+/g,"")||void 0}())){const i=Lt[t];if(i&&(n=Ht(e,i)),void 0!==n)break}return void 0===n&&(n=e),""!==t&&(n=n.replace(t,()=>i)),n}const jt={group_by_kind:!0,sort:"name",secondary_info:"none",show_server_summary:!1,show_history:!1,show_services:!1,show_icon:!0,show_state:!0,show_link:!0,show_power:!0,confirm_stop:!1,show_problem:!0,columns:1,compact:!1,show_update:!0,hide_unavailable:!1},Kt=["group_by_kind","compact","show_server_summary","show_history","show_services","show_icon","show_state","show_link","show_power","confirm_stop","show_problem","show_update","hide_unavailable"];function Bt(e){return void 0===e?"":("string"==typeof e?[e]:e).join(", ")}function It(e){return String(e??"").split(",").map(e=>e.trim()).filter(Boolean)}const Ft={show_history:!0,show_guests:!0,show_storage:!0,show_ups:!0,show_services:!0},Gt=["show_history","show_guests","show_storage","show_ups","show_services"];const Wt=["active","idle","neutral","inactive","unknown"],Vt=new Set(["running","on","active","ol","online"]),qt=new Set(["paused","frozen","standby","idle","sleeping","starting"]);function Zt(e,t){if(ht(t))return"unknown";if("disk"===e||"storage_pool"===e)return"neutral";const i=t.toLowerCase();return Vt.has(i)?"active":qt.has(i)?"idle":"inactive"}function Yt(e,t){return{running:t.filter(t=>"active"===Zt(e,t.state)).length,total:t.length,updates:t.filter(e=>"on"===e.update).length}}const Xt=["OL","OB","LB","HB","RB","CHRG","DISCHRG","BYPASS","CAL","OFF","OVER","TRIM","BOOST","FSD"];const Jt=new Set(["http:","https:","homeassistant:"]);function Qt(e,t){return(i,n)=>{if("state"===e){const e=Wt.indexOf(Zt(i.kind,t(i)))-Wt.indexOf(Zt(n.kind,t(n)));if(0!==e)return e}return i.name.localeCompare(n.name)}}function ei(e,t,i){return void 0===t||i||e.length<=t?{rows:[...e],hidden:0}:{rows:e.slice(0,t),hidden:e.length-t}}class ti{constructor(e){this.timeoutMs=e,this.timers=new Map}get size(){return this.timers.size}start(e,t){this.stop(e),this.timers.set(e,setTimeout(()=>{this.timers.delete(e),t(e)},this.timeoutMs))}stop(e){const t=this.timers.get(e);void 0!==t&&(clearTimeout(t),this.timers.delete(e))}stopAll(){for(const e of this.timers.values())clearTimeout(e);this.timers.clear()}}const ii=/\[\[(\w+)\]\]/g;function ni(e,t){return"string"==typeof e?e.replace(ii,(e,i)=>Object.hasOwn(t,i)?t[i]??"":e):Array.isArray(e)?e.map(e=>ni(e,t)):null!==e&&"object"==typeof e?Object.fromEntries(Object.entries(e).map(([e,i])=>[e,ni(i,t)])):e}function si(e,t){if("more-info"===e?.action&&e.entity)return ni(e.entity,t)||void 0}const oi=36e5;function ri(e,t){const i=[];for(const n of e[t]??[]){const e=Number(n.s);""!==n.s&&Number.isFinite(e)&&i.push([1e3*n.lu,e])}return i.sort((e,t)=>e[0]-t[0])}function ai(e,t,i,n){const s=Number(i),o=e[e.length-1];return""===i||!Number.isFinite(s)||o&&o[0]>=t?e:[...e.filter(([e])=>e>=n-oi),[t,s]]}function ci(e,t,i,n){const s=t-oi,o=e.filter(([e])=>e>=s),r=e.filter(([e])=>e<s).pop(),a=r?[[s,r[1]],...o]:[...o],c=a[a.length-1];if(c&&c[0]<t&&a.push([t,c[1]]),a.length<2)return;return a.map(([e,t],o)=>`${o?"L":"M"}${(e=>(e-s)/oi*i)(e).toFixed(1)},${(e=>n-Math.min(100,Math.max(0,e))/100*n)(t).toFixed(1)}`).join("")}class li{constructor(e){this.onChange=e,this.samples=new Map,this.requested=new Set}request(e,t){const i=t.filter(e=>!this.requested.has(e));if(i.length&&e?.callWS){for(const e of i)this.requested.add(e);this.continue(e),e.callWS({type:"history/history_during_period",start_time:new Date(Date.now()-oi).toISOString(),entity_ids:i,minimal_response:!0,no_attributes:!0}).then(e=>{const t=new Map(this.samples);for(const n of i){const i=t.get(n)??[],s=ri(e,n),o=s[s.length-1];t.set(n,[...s,...i.filter(([e])=>!o||e>o[0])])}this.update(t)}).catch(()=>{})}}continue(e){if(!this.requested.size||!e)return;let t;const i=Date.now();for(const n of this.requested){const s=e.states[n],o=this.samples.get(n)??[];if(!s)continue;const r=ai(o,Date.parse(s.last_updated)||i,s.state,i);r!==o&&(t??=new Map(this.samples),t.set(n,r))}t&&this.update(t)}update(e){this.samples=e,this.onChange(e)}}const di=["low","medium","high","critical"],hi=[50,75,90];function ui(e,t=!1){if(t)return ui(100-e);const i=hi.findIndex(t=>e<=t);return di[-1===i?di.length-1:i]}function pi(e){if(void 0===e||""===e.trim())return;const t=Number(e);return Number.isFinite(t)?Math.min(100,Math.max(0,t)):void 0}function mi(e,t){if(!t)return Dt("common.no_state_entity");const i=e;return i.formatEntityState?i.formatEntityState(t):ke(e.localize,t,e.locale)}function fi(e,t){const i=t&&!ht(t.state)?(t.state??"").split(/\s+/).filter(Boolean).map(e=>({flag:e,known:Xt.includes(e.toUpperCase())})):[];return i.length?i.map(({flag:e,known:t})=>t?Dt(`ups.${e.toUpperCase()}`):e).join(", "):mi(e,t)}function gi(e,t){const{value:i,unit:n}=function(e,t){const i=e;if(i.formatEntityStateToParts){const e=i.formatEntityStateToParts(t);return{value:e.filter(e=>"unit"!==e.type).map(e=>e.value).join("").trim(),unit:e.filter(e=>"unit"===e.type).map(e=>e.value).join("")}}const n=mi(e,t),s=t.attributes.unit_of_measurement;return s&&n.endsWith(s)?{value:n.slice(0,-s.length).trim(),unit:s}:{value:n,unit:""}}(e,t);return F`<span class="figure">${i}${n?F`<span class="unit">${n}</span>`:V}</span>`}function _i(e,t){const i=t?e?.states[t.entity_id]:void 0;return i&&!ht(i.state)?i:void 0}function vi(e,t="gauge",i=!1){const n=20,s="gauge"===t?4:8,{radius:o,circumference:r,sweep:a}=function(e){const t=(40-e)/2,i=2*Math.PI*t;return{radius:t,circumference:i,sweep:.75*i}}(s);return F`
    <svg
      class="${t} severity-${ui(e,i)}"
      viewBox="0 0 ${40} ${40}"
      aria-hidden="true"
    >
      ${G`
        <g transform="rotate(${135} ${n} ${n})">
          <circle class="track" cx=${n} cy=${n} r=${o} stroke-width=${s}
            stroke-dasharray="${a} ${r}"></circle>
          ${e>0?G`<circle class="value" cx=${n} cy=${n} r=${o} stroke-width=${s}
                  stroke-dasharray="${a*e/100} ${r}"></circle>`:V}
        </g>
      `}
    </svg>
  `}function yi(e,t,i){const n="%"===t.attributes.unit_of_measurement?pi(t.state):void 0;return F`<span class="chip" title=${Dt(`metrics.${e.label}`)}
    >${void 0===n?F`<ha-icon class="chip-icon" .icon=${e.icon}></ha-icon>`:vi(n,"mini-gauge",e.inverse)}${i}</span
  >`}function bi(e,t,i){const n=_i(e,t.entity);if(!n)return;const s=t.ref.gauge?pi(n.state):void 0,o=i?ci(i,Date.now(),100,28):void 0,r=void 0===s?"":`severity-${ui(s,t.ref.inverse)}`;return F`
    <div class="tile ${o?"with-history":""} ${r}" title=${mi(e,n)}>
      <div class="tile-icon ${void 0===s?"plain":""}">
        ${void 0===s?V:vi(s,"gauge",t.ref.inverse)}
        <ha-icon .icon=${t.ref.icon}></ha-icon>
      </div>
      <div class="tile-text">
        ${gi(e,n)}
        <span class="tile-label">${Dt(`metrics.${t.ref.label}`)}</span>
      </div>
      ${o?F`<svg
              class="spark"
              viewBox="0 0 ${100} ${28}"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              ${G`<path d=${o}></path>`}
            </svg>`:V}
    </div>
  `}function wi(e,t){const i=_i(e,t),n=function(e,t){const i=e?Date.parse(e):NaN;if(!Number.isFinite(i)||i>t)return;const n=Math.floor((t-i)/6e4);return{days:Math.floor(n/1440),hours:Math.floor(n%1440/60),minutes:n%60}}(i?.state,Date.now());if(!i||!n)return V;const s=(n.days?[[n.days,"d"],[n.hours,"h"]]:n.hours?[[n.hours,"h"],[n.minutes,"min"]]:[[n.minutes,"min"]]).map(([e,t])=>`${e} ${Dt(`units.${t}`)}`).join(" ");return F`<span class="uptime" title=${mi(e,i)}>
    <ha-icon .icon=${at.icon}></ha-icon>${Dt("metrics.uptime_for","{duration}",s)}
  </span>`}function xi(e,t){const i=t.flatMap(t=>{const i=_i(e,t.entity);return i?[F`<span
        class="service ${"on"===i.state?"on":"off"}"
        title=${`${t.ref.name}: ${mi(e,i)}`}
      >
        <ha-icon .icon=${t.ref.icon}></ha-icon>${t.ref.name}
      </span>`]:[]});return i.length?F`<div class="services">${i}</div>`:V}const $i=r`
  .uptime {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    flex: none;
    font-size: 0.8em;
    font-weight: 400;
    color: var(--secondary-text-color);
    --mdc-icon-size: 14px;
  }

  .server-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin: 4px 4px 10px;
  }

  .tile {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .tile.with-history {
    flex: 1 1 140px;
  }

  .tile-icon {
    position: relative;
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color);
  }

  /* Without a ring the icon still gets a round footprint, so a row of tiles
     keeps one rhythm — filled rather than outlined, so it does not read as a
     ring standing at zero. */
  .tile-icon.plain {
    border-radius: 50%;
    background: color-mix(in srgb, var(--secondary-text-color) 12%, transparent);
  }

  .tile-text {
    display: flex;
    flex-direction: column;
    line-height: 1.15;
  }

  .tile .figure {
    font-size: 1.05em;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .tile-label {
    font-size: 0.68em;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--secondary-text-color);
  }

  .spark {
    flex: 1;
    min-width: 48px;
    height: 28px;
    overflow: visible;
  }

  .spark path {
    fill: none;
    stroke: var(--gauge-color, var(--primary-color));
    stroke-width: 1.5;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .gauge {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .mini-gauge {
    width: 14px;
    height: 14px;
    flex: none;
  }

  .gauge circle,
  .mini-gauge circle {
    fill: none;
  }

  .gauge .track {
    stroke: var(--divider-color, rgba(127, 127, 127, 0.25));
  }

  .mini-gauge .track {
    stroke: color-mix(in srgb, currentColor 35%, transparent);
  }

  /* A fixed scale rather than the theme's accent: a ring says how loaded or
     how full something is, which a theme has no business recolouring. */
  .gauge .value,
  .mini-gauge .value {
    stroke: var(--gauge-color);
    stroke-linecap: round;
    transition: stroke-dasharray 0.3s ease;
  }

  .severity-low {
    --gauge-color: var(--green-color, #43a047);
  }

  .severity-medium {
    --gauge-color: var(--amber-color, #ffc107);
  }

  .severity-high {
    --gauge-color: var(--orange-color, #fb8c00);
  }

  .severity-critical {
    --gauge-color: var(--red-color, #e53935);
  }

  .services {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 4px 10px;
  }

  /* Lit like a running row while the service is on, dimmed while it is off. */
  .service {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px 2px 6px;
    border-radius: 12px;
    font-size: 0.78em;
    --mdc-icon-size: 14px;
  }

  .service.on {
    color: var(--success-color, #43a047);
    background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent);
  }

  .service.off {
    color: var(--secondary-text-color);
    background: color-mix(in srgb, var(--secondary-text-color) 10%, transparent);
    opacity: 0.7;
  }

  /* A measurement in a line: what it is in front, kept together as one unit
     so the line breaks between measurements and never inside one. */
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    white-space: nowrap;
    vertical-align: bottom;
  }

  .chip-icon {
    --mdc-icon-size: 14px;
    opacity: 0.8;
  }

  /* A figure wraps as a whole: a number on one line and its unit on the next
     reads as two values. */
  .figure {
    white-space: nowrap;
  }

  .unit {
    margin-left: 0.15em;
    font-size: 0.75em;
    font-weight: 400;
    opacity: 0.8;
  }

  @media (prefers-reduced-motion: reduce) {
    .gauge .value,
    .mini-gauge .value {
      transition: none;
    }
  }
`
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */;class ki{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,i){this._$Ct=e,this._$AM=t,this._$Ci=i}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}}const Si=(e,t,i)=>{Ae(e,t,i)},Ai="ontouchstart"in window||navigator.maxTouchPoints>0||"msMaxTouchPoints"in navigator&&navigator.msMaxTouchPoints>0,Ei=()=>{const e=document.body,t=e.querySelector(".action-handler-mos-card");if(t)return t;const i=document.createElement("div");i.className="action-handler-mos-card",i.style.position="absolute",i.style.width=Ai?"100px":"50px",i.style.height=Ai?"100px":"50px",i.style.transform="translate(-50%, -50%) scale(0)",i.style.pointerEvents="none",i.style.zIndex="999",i.style.transition="transform 0.1s ease-out",i.style.borderRadius="50%",i.style.background="rgba(var(--rgb-primary-color), 0.3)";const n=i;n.holdTime=500,n.cancelled=!1,n.held=!1,n.timer=void 0,n.dblClickTimeout=void 0,n.isRepeating=!1,n.repeatTimeout=void 0,e.appendChild(i);const s=(e=>{const t=e;return t.startAnimation=(e,i)=>{Object.assign(t.style,{left:`${e}px`,top:`${i}px`,transform:"translate(-50%, -50%) scale(1)"})},t.stopAnimation=()=>{Object.assign(t.style,{left:"",top:"",transform:"translate(-50%, -50%) scale(0)"})},t.bind=(e,i={})=>{if(e.actionHandler&&Ee(i,e.actionHandler.options))return;if(e.actionHandler?(e.removeEventListener("touchstart",e.actionHandler.start),e.removeEventListener("touchend",e.actionHandler.end),e.removeEventListener("touchcancel",e.actionHandler.end),e.removeEventListener("mousedown",e.actionHandler.start),e.removeEventListener("click",e.actionHandler.end),e.removeEventListener("keydown",e.actionHandler.handleKeyDown),e.actionHandler.handleTouchMove&&e.removeEventListener("touchmove",e.actionHandler.handleTouchMove)):e.addEventListener("contextmenu",e=>{const t=e||window.event;return t.preventDefault&&t.preventDefault(),t.stopPropagation&&t.stopPropagation(),t.cancelBubble=!0,t.returnValue=!1,!1}),e.actionHandler={options:i},i.disabled)return;e.actionHandler.start=n=>{if(n.detail?.ignore)return;let s,o;t.cancelled=!1,t.held=!1,n.touches?(s=n.touches[0].clientX,o=n.touches[0].clientY):(s=n.clientX,o=n.clientY),i.hasHold&&(t.timer=window.setTimeout(()=>{if(t.startAnimation(s,o),t.held=!0,Si(e,"action",{action:"hold"}),i.repeat&&i.repeat>0){let n=0;t.isRepeating=!0,t.repeatTimeout=window.setInterval(()=>{n++,Si(e,"action",{action:"hold"}),i.repeatLimit&&n>=i.repeatLimit&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1)},i.repeat)}},t.holdTime))},e.actionHandler.end=n=>{if(!n.detail?.ignore)return["touchend","touchcancel"].includes(n.type)&&t.cancelled?(t.isRepeating&&t.repeatTimeout&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1),void(i.isMomentary&&Si(e,"action",{action:"release"}))):void("touchcancel"!==n.type&&(["touchend","touchcancel","mouseup"].includes(n.type)&&t.stopAnimation(),t.isRepeating&&t.repeatTimeout&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1),t.timer&&(clearTimeout(t.timer),t.timer=void 0),t.held||(i.hasDoubleClick?"click"===n.type&&n.detail<2||!t.dblClickTimeout?t.dblClickTimeout=window.setTimeout(()=>{t.dblClickTimeout=void 0,Si(e,"action",{action:"tap"})},250):(clearTimeout(t.dblClickTimeout),t.dblClickTimeout=void 0,Si(e,"action",{action:"double_tap"})):Si(e,"action",{action:"tap"})),i.isMomentary&&Si(e,"action",{action:"release"})))},i.disableKbd||(e.actionHandler.handleKeyDown=t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),e.click())});const n=i=>{if(!i.touches)return;const n=i.touches[0],s=e.getBoundingClientRect(),o=n.clientX-s.left,r=n.clientY-s.top;(o<0||r<0||o>=s.width||r>=s.height)&&(t.cancelled=!0)};e.actionHandler.handleTouchMove=n,e.addEventListener("touchstart",e.actionHandler.start,{passive:!0}),e.addEventListener("touchmove",n,{passive:!0}),e.addEventListener("touchend",e.actionHandler.end),e.addEventListener("touchcancel",e.actionHandler.end),e.addEventListener("mousedown",e.actionHandler.start,{passive:!0}),e.addEventListener("click",e.actionHandler.end),i.disableKbd||e.addEventListener("keydown",e.actionHandler.handleKeyDown)},["touchcancel","mouseout","mouseup","touchmove","mousewheel","wheel","scroll"].forEach(e=>{document.addEventListener(e,()=>{t.cancelled=!0,t.timer&&(t.stopAnimation(),clearTimeout(t.timer),t.timer=void 0,t.isRepeating&&t.repeatTimeout&&(window.clearInterval(t.repeatTimeout),t.isRepeating=!1))},{passive:!0})}),t})(i);return s};const Ci=(e=>(...t)=>({_$litDirective$:e,values:t}))(class extends ki{constructor(e){super(e)}render(e){}update(e,[t]){return Ee(t,this.previousOptions)||(((e,t)=>{const i=Ei();i&&i.bind(e,t)})(e.element,t),this.previousOptions=t?{...t}:void 0),this.render(t)}});async function Mi(e,t,i){return await e().whenDefined("home-assistant"),function(e,t,i){return!e.get(t)&&(e.define(t,i),!0)}(e(),t,i)}function Ti(e,t){const i=e??[];return i.some(e=>e.type===t.type)||i.push(t),i}const Pi=Ue.filter(e=>Ie[e].hasPower),Oi={docker_container:{translationKey:"memory_docker",keySuffix:"memory_docker",label:"memory",icon:"mdi:memory"},lxc_container:{translationKey:"memory_lxc",keySuffix:"memory_lxc",label:"memory",icon:"mdi:memory"},virtual_machine:{translationKey:"memory_vms",keySuffix:"memory_vms",label:"memory",icon:"mdi:memory"}};function zi(e){const t=e.filter(e=>void 0!==e&&""!==e.trim()).map(Number).filter(Number.isFinite);return t.length?t.reduce((e,t)=>e+t,0):void 0}const Li=(...e)=>e.filter(e=>void 0!==e).map(e=>e.entity_id),Ni=(e,t)=>{const i=e(t.entity_id);return"problem"===i?.attributes.device_class&&"on"===i.state};function Ui(e,t,i,n){const s=qe(t),o=s.get(i.id)??[],r=e=>e?n(e.entity_id)?.state:void 0,a=Pi.flatMap(t=>{const n=Ve(e,[t],i.id);if(!n.length)return[];const[a]=ot(t,"cpu"),c=Oi[t],l=c?it(o,c):void 0,d=n.map(e=>{const i=s.get(e.id)??[];return{stateEntity:Ze(i,t),updateEntity:Xe(i,t),cpuEntity:a?it(i,a):void 0}});return[{kind:t,counts:Yt(t,d.map(e=>({state:r(e.stateEntity),update:r(e.updateEntity)}))),cpu:zi(d.map(e=>r(e.cpuEntity))),memory:l,entityIds:[...Li(l),...d.flatMap(e=>Li(e.stateEntity,e.updateEntity,e.cpuEntity))]}]}),c=Ve(e,["disk"],i.id);let l;if(c.length){const[,e]=ot("disk","auto"),t=c.map(t=>{const i=s.get(t.id)??[];return{power:Ze(i,"disk"),temperature:e?it(i,e):void 0,problems:tt(i)}}),i=t.map(e=>e.temperature).filter(e=>void 0!==e).filter(e=>Number.isFinite(Number(r(e)))).sort((e,t)=>Number(r(t))-Number(r(e)))[0];l={total:c.length,standby:t.filter(e=>"standby"===r(e.power)).length,hottest:i,problems:t.filter(e=>e.problems.some(e=>Ni(n,e))).length,entityIds:t.flatMap(e=>[...Li(e.power,e.temperature),...Li(...e.problems)])}}const d=Ve(e,["storage_pool"],i.id).map(e=>{const t=s.get(e.id)??[],i=Ze(t,"storage_pool"),[n]=ot("storage_pool","auto"),o=it(t,n),r=o?{ref:n,entity:o,over:n.over&&it(t,n.over)}:void 0,a=nt(t,"storage_pool"),c=tt(t);return{device:e,usage:i,free:r,activities:a,problems:c,entityIds:[...Li(i,r?.entity,r?.over),...a.map(e=>e.entity.entity_id),...Li(...c)]}}),h=Ve(e,["ups"],i.id).map(e=>{const t=s.get(e.id)??[],i=Ze(t,"ups"),n=ot("ups","auto").flatMap(e=>{const i=it(t,e);return i?[{ref:e,entity:i}]:[]}),o=tt(t);return{device:e,status:i,metrics:n,problems:o,entityIds:[...Li(i),...n.map(e=>e.entity.entity_id),...Li(...o)]}});return{kinds:a,disks:l,pools:d,ups:h}}function Ri(e,t){return t.filter(t=>Ni(e,t)).length}const Hi=window;Hi.customCards=Ti(Hi.customCards,{type:"mos-overview-card",name:"MOS NAS Overview",description:"A MOS NAS server at a glance: load, guests, storage, UPS and services"});const Di={label:"memory",icon:"mdi:memory"};class ji extends le{constructor(){super(...arguments),this.history=new Map,this.historyLoader=new li(e=>{this.history=e}),this.unsubscribe=[],this.states=e=>this.hass?.states[e]}static async getConfigElement(){const{overviewEditorDefined:e}=await Promise.resolve().then(function(){return Wi});return await e,document.createElement("mos-overview-card-editor")}static getStubConfig(){return{}}setConfig(e){this.config=function(e){if(!e)throw new Error(Dt("common.invalid_configuration"));for(const t of Gt)if(void 0!==e[t]&&"boolean"!=typeof e[t])throw new Error(`${Dt("errors.not_a_boolean")}: ${t}`);if(void 0!==e.navigation_path&&"string"!=typeof e.navigation_path)throw new Error(`${Dt("errors.not_a_string")}: navigation_path`);return{...Ft,...e}}(e)}connectedCallback(){super.connectedCallback(),this.subscribeRegistries()}disconnectedCallback(){super.disconnectedCallback();for(const e of this.unsubscribe)e();this.unsubscribe=[]}getCardSize(){return 6}getGridOptions(){return{columns:12,rows:"auto",min_columns:6}}willUpdate(e){e.has("hass")&&(Rt(this.hass?.locale?.language),this.historyLoader.continue(this.hass))}updated(e){e.has("hass")&&!this.unsubscribe.length&&this.subscribeRegistries(),this.config.show_history&&this.historyLoader.request(this.hass,this.sections().flatMap(e=>e.metrics.filter(e=>e.ref.gauge).map(e=>e.entity.entity_id)))}shouldUpdate(e){if(!this.config)return!1;if(!this.unsubscribe.length&&this.isConnected)return!0;if(e.has("config")||e.has("devices")||e.has("entities")||e.has("history"))return!0;const t=e.get("hass");return e.has("hass")&&t?t.locale!==this.hass.locale||t.localize!==this.hass.localize||this.trackedEntityIds().some(e=>t.states[e]!==this.hass.states[e]):e.has("hass")}subscribeRegistries(){!this.unsubscribe.length&&this.isConnected&&this.hass?.connection&&(this.unsubscribe=[Fe(this.hass.connection,e=>{this.devices=e}),Ge(this.hass.connection,e=>{this.entities=e})])}sections(){if(!this.devices||!this.entities)return[];const e=qe(this.entities);return We(this.devices).filter(e=>!this.config.server||e.id===this.config.server).map(t=>{const i=e.get(t.id)??[];return{server:t,name:dt(t),metrics:st(i,rt),bootTime:it(i,at),services:this.config.show_services?lt(i):[]}})}trackedEntityIds(){const e=this.trackedCache;if(e&&e.devices===this.devices&&e.entities===this.entities&&e.config===this.config)return e.ids;const t=[];if(this.devices&&this.entities)for(const e of this.sections()){const i=Ui(this.devices,this.entities,e.server,this.states);t.push(...e.metrics.map(e=>e.entity.entity_id),...e.services.map(e=>e.entity.entity_id),...e.bootTime?[e.bootTime.entity_id]:[],...i.kinds.flatMap(e=>e.entityIds),...i.disks?.entityIds??[],...i.pools.flatMap(e=>e.entityIds),...i.ups.flatMap(e=>e.entityIds))}return this.trackedCache={devices:this.devices,entities:this.entities,config:this.config,ids:t},t}render(){return F`
      <ha-card .header=${this.config.title}>
        <div class="card-content">${this.renderBody()}</div>
      </ha-card>
    `}renderBody(){if(!this.devices||!this.entities)return F`<div class="notice">${Dt("common.loading")}</div>`;const e=this.sections();return e.length?e.map(e=>this.renderServer(e)):F`<div class="notice">${Dt("common.no_devices")}</div>`}renderServer(e){const t=Ui(this.devices??[],this.entities??[],e.server,this.states),i=e.metrics.map(e=>bi(this.hass,e,this.config.show_history?this.history.get(e.entity.entity_id):void 0)).filter(e=>void 0!==e);return F`
      <section class="server">
        <div class="server-heading">
          <span class="server-name"><ha-icon icon="mdi:nas"></ha-icon>${e.name}</span>
          ${wi(this.hass,e.bootTime)}
        </div>
        ${i.length?F`<div class="server-summary">${i}</div>`:V}
        ${this.config.show_guests?this.renderGuests(t):V}
        ${this.config.show_storage?this.renderStorage(t,e.name):V}
        ${this.config.show_ups?this.renderUps(t.ups,e.name):V}
        ${xi(this.hass,e.services)}
      </section>
    `}renderGuests(e){return e.kinds.length?F`
      <div class="heading">${Dt("overview.guests")}</div>
      <div class="kinds">${e.kinds.map(e=>this.renderKind(e))}</div>
    `:V}renderKind(e){const{running:t,total:i,updates:n}=e.counts,s=_i(this.hass,e.memory),o=this.config.navigation_path?.replace(/\[\[kind]]/g,e.kind),r=void 0===e.cpu?V:F`<span class="chip" title=${Dt("metrics.cpu")}
            >${vi(pi(String(e.cpu))??0,"mini-gauge")}<span class="figure"
              >${this.formatNumber(e.cpu)}<span class="unit">%</span></span
            ></span
          >`;return F`
      <div
        class="kind ${t?"running":""} ${o?"clickable":""}"
        role=${o?"link":V}
        tabindex=${o?"0":V}
        @click=${()=>this.navigate(o)}
        @keydown=${e=>"Enter"===e.key&&this.navigate(o)}
      >
        <div class="kind-icon"><ha-icon .icon=${Ie[e.kind].icon}></ha-icon></div>
        <div class="kind-text">
          <span class="kind-name">${Dt(`kinds.${e.kind}`)}</span>
          <span class="kind-line">
            <span class="figure">${t}<span class="of">/</span>${i}</span>
            ${Dt("overview.running")}
            ${n?F`<span class="updates"
                    >· ${Dt(1===n?"counts.update":"counts.updates","{count}",String(n))}</span
                  >`:V}
          </span>
          ${t?F`<span class="kind-line metrics">
                  ${r} ${s?yi(Di,s,gi(this.hass,s)):V}
                </span>`:V}
        </div>
      </div>
    `}renderStorage(e,t){return e.pools.length||e.disks?F`
      <div class="heading">${Dt("overview.storage")}</div>
      ${e.pools.map(e=>this.renderPool(e,t))}
      ${e.disks?this.renderDisks(e.disks):V}
    `:V}renderPool(e,t){const i=_i(this.hass,e.usage),n=i?pi(i.state):void 0,s=e.free?_i(this.hass,e.free.entity):void 0,o=e.free?.over?_i(this.hass,e.free.over):void 0,r=Ri(this.states,e.problems),a=e.activities.filter(e=>"on"===this.hass.states[e.entity.entity_id]?.state);return F`
      <div class="pool" @click=${()=>this.moreInfo(e.usage)}>
        <div class="pool-head">
          <span class="pool-name">
            ${r?F`<ha-icon class="problem" icon="mdi:alert"></ha-icon>`:V}
            ${dt(e.device,t)}
          </span>
          <span class="pool-figures">
            ${i?gi(this.hass,i):V}
            ${s?F`<span class="pool-free" title=${Dt("overview.free_of_total")}
                    >${gi(this.hass,s)}
                    ${Dt("overview.free")}${o?F`<span class="of">/</span>${gi(this.hass,o)}`:V}</span
                  >`:V}
          </span>
        </div>
        <div class="bar severity-${ui(n??0)}">
          <div class="bar-fill" style="width: ${n??0}%"></div>
        </div>
        ${a.length?F`<div class="pool-jobs">
                ${a.map(e=>F`<span class="chip activity"
                      ><ha-icon class="chip-icon" .icon=${e.ref.icon}></ha-icon>${Dt(`metrics.${e.ref.label}`)}</span
                    >`)}
              </div>`:V}
      </div>
    `}renderDisks(e){const t=_i(this.hass,e.hottest);return F`
      <div class="disks">
        <ha-icon icon="mdi:harddisk"></ha-icon>
        <span>${Dt("overview.disks","{count}",String(e.total))}</span>
        ${e.standby?F`<span class="part"
                ><span class="separator">·</span>
                ${Dt("overview.standby","{count}",String(e.standby))}</span
              >`:V}
        ${t?F`<span class="part"
                ><span class="separator">·</span>
                <span class="chip"
                  ><ha-icon class="chip-icon" icon="mdi:thermometer"></ha-icon>${Dt("overview.max")}
                  ${gi(this.hass,t)}</span
                ></span
              >`:V}
        ${e.problems?F`<span class="part problem-text"
                ><span class="separator">·</span> <ha-icon class="chip-icon" icon="mdi:alert"></ha-icon>${Dt("overview.problems","{count}",String(e.problems))}</span
              >`:V}
      </div>
    `}renderUps(e,t){return e.length?F`
      <div class="heading">${Dt("overview.power")}</div>
      ${e.map(e=>{const i=_i(this.hass,e.status),n=Ri(this.states,e.problems),s=e.metrics.flatMap(e=>{const t=_i(this.hass,e.entity);return t?[yi(e.ref,t,gi(this.hass,t))]:[]});return F`
          <div class="ups ${n?"alert":""}" @click=${()=>this.moreInfo(e.status)}>
            <ha-icon icon=${n?"mdi:power-plug-off":"mdi:power-plug"}></ha-icon>
            <span class="ups-name">${dt(e.device,t)}</span>
            ${i?F`<span class="ups-status">${fi(this.hass,i)}</span>`:V}
            <span class="ups-metrics">${s}</span>
          </div>
        `})}
    `:V}formatNumber(e){return new Intl.NumberFormat(this.hass?.locale?.language,{maximumFractionDigits:e<10?2:1}).format(e)}navigate(e){e&&Pe(this,this.hass,{tap_action:{action:"navigate",navigation_path:e}},"tap")}moreInfo(e){e&&Pe(this,this.hass,{entity:e.entity_id,tap_action:{action:"more-info"}},"tap")}static get styles(){return[$i,r`
        .card-content {
          padding: 4px 16px 16px;
        }

        .notice {
          padding: 16px 0;
          color: var(--secondary-text-color);
          text-align: center;
        }

        .server + .server {
          margin-top: 16px;
          padding-top: 8px;
          border-top: 1px solid var(--divider-color);
        }

        .server-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin: 14px 4px 8px;
        }

        .server-name {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 1.15em;
          font-weight: 500;
          color: var(--primary-text-color);
          --mdc-icon-size: 22px;
        }

        .server-name ha-icon {
          color: var(--state-icon-color, var(--primary-color));
        }

        .heading {
          margin: 14px 4px 6px;
          font-size: 0.75em;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--secondary-text-color);
        }

        /* Lifted off the card the same way the list card's rows are, so the two
           cards read as one family. */
        .kind,
        .pool,
        .disks,
        .ups {
          --tile-background: color-mix(
            in srgb,
            var(--primary-text-color) 7%,
            var(--ha-card-background, var(--card-background-color))
          );
          border-radius: 12px;
          background: var(--tile-background);
        }

        .kinds {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }

        @container (max-width: 340px) {
          .kinds {
            grid-template-columns: 1fr;
          }
        }

        .card-content {
          container-type: inline-size;
        }

        .kind {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          min-width: 0;
        }

        .kind.clickable {
          cursor: pointer;
        }

        .kind.clickable:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .kind-icon {
          flex: none;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          color: var(--secondary-text-color);
          background: color-mix(in srgb, var(--secondary-text-color) 14%, transparent);
          --mdc-icon-size: 22px;
        }

        .kind.running .kind-icon {
          color: var(--success-color, var(--state-active-color, #43a047));
          background: color-mix(in srgb, var(--success-color, var(--state-active-color, #43a047)) 18%, transparent);
        }

        .kind-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }

        .kind-name {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .kind-line {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 2px 8px;
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }

        .kind-line .figure {
          font-weight: 600;
          color: var(--primary-text-color);
        }

        .kind-line.metrics .figure {
          font-weight: 500;
        }

        .updates {
          color: var(--warning-color, #ffa600);
        }

        .of {
          margin: 0 1px;
          opacity: 0.6;
        }

        .pool {
          padding: 10px 12px;
          margin-bottom: 8px;
          cursor: pointer;
        }

        .pool-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
        }

        .pool-name {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
        }

        .pool-figures {
          display: inline-flex;
          gap: 10px;
          flex: none;
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }

        .pool-figures > .figure {
          font-weight: 600;
          color: var(--primary-text-color);
        }

        .bar {
          height: 6px;
          margin-top: 8px;
          border-radius: 3px;
          overflow: hidden;
          background: var(--divider-color, rgba(127, 127, 127, 0.25));
        }

        .bar-fill {
          height: 100%;
          border-radius: 3px;
          background: var(--gauge-color);
          transition: width 0.3s ease;
        }

        .pool-jobs {
          margin-top: 6px;
          font-size: 0.85em;
        }

        .chip.activity {
          color: var(--info-color, var(--primary-color));
        }

        .disks,
        .ups {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 4px 8px;
          padding: 10px 12px;
          margin-bottom: 8px;
          font-size: 0.9em;
          color: var(--secondary-text-color);
          --mdc-icon-size: 18px;
        }

        .ups {
          cursor: pointer;
        }

        .ups-name {
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .ups-status {
          color: var(--success-color, var(--state-active-color, #43a047));
        }

        .ups.alert .ups-status,
        .ups.alert > ha-icon,
        .problem,
        .problem-text {
          color: var(--error-color, #db4437);
        }

        .ups-metrics {
          display: inline-flex;
          flex-wrap: wrap;
          gap: 4px 10px;
          margin-left: auto;
        }

        .separator {
          opacity: 0.6;
        }

        /* A part carries the separator in front of it, so a line that wraps
           breaks before a "·" and never leaves one on its own. */
        .part {
          white-space: nowrap;
        }

        @media (prefers-reduced-motion: reduce) {
          .bar-fill {
            transition: none;
          }
        }
      `]}}e([pe({attribute:!1})],ji.prototype,"hass",void 0),e([me()],ji.prototype,"config",void 0),e([me()],ji.prototype,"devices",void 0),e([me()],ji.prototype,"entities",void 0),e([me()],ji.prototype,"history",void 0),Mi(()=>customElements,"mos-overview-card",ji);const Ki=window;Ki.customCards=Ti(Ki.customCards,{type:"mos-card",name:"MOS NAS Card",description:"Containers, Compose stacks, VMs, disks, pools and the UPS of a MOS NAS server"});const Bi={label:"used",icon:"mdi:database"};class Ii extends le{constructor(){super(...arguments),this.pending=new Map,this.expanded=new Set,this.history=new Map,this.historyLoader=new li(e=>{this.history=e}),this.pendingTimers=new ti(2e4),this.unsubscribe=[]}static async getConfigElement(){const{editorDefined:e}=await Promise.resolve().then(function(){return Xi});return await e,document.createElement("mos-card-editor")}static getStubConfig(){return{kinds:[...Ue]}}setConfig(e){this.config=function(e){if(!e)throw new Error(Dt("common.invalid_configuration"));if(void 0!==e.kinds){if(!Array.isArray(e.kinds))throw new Error(Dt("errors.kinds_not_a_list"));const t=e.kinds.filter(e=>!De(e));if(t.length)throw new Error(`${Dt("errors.unknown_kind")}: ${t.join(", ")}`);if(!e.kinds.length)throw new Error(Dt("errors.no_kinds"))}if(void 0!==e.sort&&!He.includes(e.sort))throw new Error(`${Dt("errors.unknown_sort")}: ${e.sort}`);if(void 0!==e.secondary_info&&!je.includes(e.secondary_info))throw new Error(`${Dt("errors.unknown_secondary_info")}: ${e.secondary_info}`);if(void 0!==e.max_rows&&(!Number.isInteger(e.max_rows)||e.max_rows<1))throw new Error(`${Dt("errors.bad_max_rows")}: ${e.max_rows}`);if(void 0!==e.columns&&(!Number.isInteger(e.columns)||e.columns<1||e.columns>2))throw new Error(`${Dt("errors.bad_columns")}: ${e.columns}`);return{kinds:[...Ue],...jt,tap_action:{action:"more-info"},...e}}(e)}connectedCallback(){super.connectedCallback(),this.subscribeRegistries(),this.resumePendingTimers()}disconnectedCallback(){super.disconnectedCallback(),this.unsubscribeRegistries(),this.pendingTimers.stopAll()}willUpdate(e){if(e.has("hass")&&(Rt(this.hass?.locale?.language),this.historyLoader.continue(this.hass)),e.has("hass")&&this.pending.size)for(const e of function(e,t){const i=[];for(const[n,s]of e)(t(n)??"")!==s&&i.push(n);return i}(this.pending,e=>this.hass.states[e]?.state))this.clearPending(e)}updated(e){e.has("hass")&&!this.unsubscribe.length&&this.subscribeRegistries(),this.historyLoader.request(this.hass,this.historyEntityIds())}historyEntityIds(){if(!(this.config.show_server_summary&&this.config.show_history&&this.devices&&this.entities))return[];const e=qe(this.entities);return We(this.devices).flatMap(t=>st(e.get(t.id)??[],rt).filter(e=>e.ref.gauge).map(e=>e.entity.entity_id))}shouldUpdate(e){if(!this.config)return!1;if(!this.unsubscribe.length&&this.isConnected)return!0;if(e.has("config")||e.has("devices")||e.has("entities")||e.has("icons")||e.has("pending")||e.has("expanded")||e.has("history"))return!0;if(!e.has("hass"))return!1;const t=e.get("hass");return!t||(t.locale!==this.hass.locale||t.localize!==this.hass.localize||this.trackedEntityIds().some(e=>t.states[e]!==this.hass.states[e]))}trackedEntityIds(){const e=this.trackedCache;if(e&&e.devices===this.devices&&e.entities===this.entities&&e.config===this.config)return e.ids;const t=[];if(this.devices&&this.entities){const e=this.config.kinds??[...Ue],i=qe(this.entities);for(const n of Ve(this.devices,e,this.config.server)){const e=i.get(n.id)??[],s=n.model_id,o=Ze(e,s),r=Ye(e,s);o&&t.push(o.entity_id),r&&t.push(r.entity_id);for(const i of this.rowMetrics(e,s))t.push(i.entity.entity_id),i.over&&t.push(i.over.entity_id);if(this.config.show_update){const i=Xe(e,s);i&&t.push(i.entity_id)}if(this.config.show_problem)for(const i of tt(e))t.push(i.entity_id);for(const i of nt(e,s))t.push(i.entity.entity_id)}for(const e of We(this.devices)){const n=i.get(e.id)??[];if(this.config.show_server_summary){for(const e of st(n,rt))t.push(e.entity.entity_id);const e=it(n,at);e&&t.push(e.entity_id)}if(this.config.show_services)for(const e of lt(n))t.push(e.entity.entity_id)}}return this.trackedCache={devices:this.devices,entities:this.entities,config:this.config,ids:t},t}subscribeRegistries(){var e,t;!this.unsubscribe.length&&this.isConnected&&this.hass?.connection&&(this.unsubscribe=[Fe(this.hass.connection,e=>{this.devices=e}),Ge(this.hass.connection,e=>{this.entities=e})],(e=this.hass.connection,t="mos",e.sendMessagePromise({type:"frontend/get_icons",category:"entity",integration:t}).then(e=>e.resources?.[t]??{})).then(e=>{this.icons=e}).catch(()=>{}))}unsubscribeRegistries(){for(const e of this.unsubscribe)e();this.unsubscribe=[]}getCardSize(){const e=this.buildSections();if(!e)return 3;const t=e.reduce((e,t)=>e+t.groups.reduce((e,t)=>e+t.rows.length,0),0);return Math.max(3,t+1)}getGridOptions(){return{columns:12,rows:"auto",min_columns:6}}buildSections(){if(!this.devices||!this.entities||!this.config)return;const e=this.config.kinds??[...Ue],t=qe(this.entities),i=this.config.server?this.devices.filter(e=>e.id===this.config.server):We(this.devices),n=this.config.server?[]:function(e,t,i){const n=new Set(i);return Ve(e,t).filter(e=>!n.has(e.via_device_id))}(this.devices,e,i.map(e=>e.id)),s=this.config.server?[this.config.server]:[...i.map(e=>e.id),...n.length?[void 0]:[]],o=[];for(const r of s){const s=i.find(e=>e.id===r),a=s&&(s.name_by_user||s.name)||void 0,c=void 0===r?n:Ve(this.devices,e,r),l=[];for(const i of e){const e=c.filter(e=>e.model_id===i).map(e=>{const n=t.get(e.id)??[];return{device:e,kind:i,name:dt(e,a),stateEntity:Ze(n,i),powerEntity:Ye(n,i),updateEntity:Xe(n,i),metrics:this.rowMetrics(n,i),problemCandidates:this.config.show_problem?tt(n):[],activities:nt(n,i)}}).filter(e=>et(e.name,this.config.filter)).filter(e=>!this.config.hide_unavailable||!ht(this.stateValue(e))).sort(Qt(this.config.sort,e=>this.stateValue(e)));if(e.length){const t=`${r??""}:${i}`,n=Yt(i,e.map(e=>({state:this.stateValue(e),update:e.updateEntity?this.hass?.states[e.updateEntity.entity_id]?.state:void 0})));l.push({kind:i,key:t,counts:n,...ei(e,this.config.max_rows,this.expanded.has(t))})}}if(l.length){const e=s?t.get(s.id)??[]:[],i=this.config.show_server_summary&&s;o.push({server:s,groups:l,serverMetrics:i?st(e,rt):[],bootTime:i?it(e,at):void 0,services:this.config.show_services&&s?lt(e):[]})}}return o}stateValue(e){return e.stateEntity?this.hass?.states[e.stateEntity.entity_id]?.state:void 0}rowMetrics(e,t){const i=this.config.secondary_info??"none";return"none"===i?[]:st(e,ot(t,i))}render(){return F`
      <ha-card .header=${this.config.title}>
        <div class="card-content">${this.renderBody()}</div>
      </ha-card>
    `}renderBody(){const e=this.buildSections();return void 0===e?this.renderNotice(Dt("common.loading")):0===e.length?this.renderNotice(Dt("common.no_devices")):e.map(t=>this.renderSection(t,e.length>1))}renderNotice(e){return F`<div class="notice">${e}</div>`}renderSection(e,t){const i=e.server&&(e.server.name_by_user||e.server.name)||Dt("common.server"),n=e.serverMetrics.map(e=>bi(this.hass,e,this.history.get(e.entity.entity_id))).filter(e=>void 0!==e),s=xi(this.hass,e.services),o=wi(this.hass,e.bootTime);return F`
      ${t||n.length||s!==V?F`
              <div class="server-heading"><span>${i}</span>${o}</div>
              ${n.length?F`<div class="server-summary">${n}</div>`:V} ${s}
            `:V}
      ${e.groups.map(e=>this.renderGroup(e))}
    `}renderGroup(e){return F`
      ${this.config.group_by_kind?F`<div class="kind-heading">
              <span>${Dt(`kinds.${e.kind}`)}</span>${this.renderCounts(e)}
            </div>`:V}
      <div class="group cols-${this.config.columns??1}">${e.rows.map(e=>this.renderRow(e))}</div>
      ${this.renderMore(e)}
    `}renderCounts(e){if(!Ie[e.kind].hasPower)return V;const{running:t,total:i,updates:n}=e.counts;return F`<span class="kind-counts">
      ${Dt("counts.running","{running}",String(t)).replace("{total}",String(i))}
      ${this.config.show_update&&n?F`<span class="kind-updates"
              >· ${Dt(1===n?"counts.update":"counts.updates","{count}",String(n))}</span
            >`:V}
    </span>`}renderMore(e){return e.hidden?F`
      <button class="more" @click=${()=>this.expandGroup(e.key)}>
        ${Dt("common.show_more","{count}",String(e.hidden))}
      </button>
    `:V}expandGroup(e){this.expanded=new Set(this.expanded).add(e)}renderRow(e){const t=e.stateEntity?this.hass.states[e.stateEntity.entity_id]:void 0,i=ht(t?.state);return F`
      <div
        class="row ${i?"unavailable":""} ${this.config.compact?"compact":""} tone-${Zt(e.kind,t?.state)}"
      >
        <div
          class="row-body"
          @action=${t=>this.handleAction(t,e)}
          ${Ci({hasHold:Oe(this.config.hold_action),hasDoubleClick:Oe(this.config.double_tap_action)})}
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
    `}renderIcon(e,t){return F`
      <div class="icon-wrap">
        ${this.renderArtwork(e,t)}${this.renderProblemBadge(e)}${this.renderUpdateBadge(e)}
      </div>
    `}renderProblemBadge(e){if(!this.config.show_problem)return V;const t=e.problemCandidates.map(e=>this.hass.states[e.entity_id]).filter(e=>"problem"===e?.attributes.device_class&&"on"===e.state);if(!t.length)return V;const i=t.map(t=>this.problemName(e,t)).filter(Boolean).join(", ")||Dt("common.problem");return F`
      <div class="problem-badge" role="img" aria-label=${i} title=${i}>
        <ha-icon icon="mdi:alert"></ha-icon>
      </div>
    `}problemName(e,t){const i=t.attributes.friendly_name??"",n=e.device.name_by_user||e.device.name||"";return n&&i.startsWith(`${n} `)?i.slice(n.length+1):i}renderArtwork(e,t){const i=t?.attributes.entity_picture;if(i)return F`<img class="icon picture" src=${i} alt="" loading="lazy" />`;const n=t?.attributes.icon||function(e,t,i){if(!e||!t?.translation_key)return;const n=t.entity_id.split(".")[0],s=e[n]?.[t.translation_key];return s?(void 0!==i?s.state?.[i]:void 0)??s.default:void 0}(this.icons,e.stateEntity,t?.state)||Ie[e.kind].icon;return F`<ha-icon class="icon" .icon=${n}></ha-icon>`}renderUpdateBadge(e){if(!this.config.show_update||!e.updateEntity)return V;if("on"!==this.hass.states[e.updateEntity.entity_id]?.state)return V;const t=Dt("common.update_available");return F`
      <div class="update-badge" role="img" aria-label=${t} title=${t}>
        <ha-icon icon="mdi:arrow-up"></ha-icon>
      </div>
    `}renderSecondary(e,t){const i=[],n="none"!==(this.config.secondary_info??"none");this.config.show_state&&n&&"storage_pool"===e.kind&&t&&!ht(t.state)?i.push(yi(Bi,t,gi(this.hass,t))):this.config.show_state&&i.push("ups"===e.kind?fi(this.hass,t):mi(this.hass,t));const s=function(e,t){if(!Ie[e].hasPower)return!0;const i=Zt(e,t);return"active"===i||"idle"===i}(e.kind,t?.state)?e.metrics.map(e=>this.renderMetric(e)).filter(e=>void 0!==e):[];return i.push(...s,...this.renderActivities(e)),i.length?F`<span class="state ${s.length?"with-metrics":""}"
      >${i.map((e,t)=>t?F` <span class="part"><span class="separator">·</span> ${e}</span>`:e)}</span
    >`:V}renderActivities(e){return e.activities.filter(e=>"on"===this.hass?.states[e.entity.entity_id]?.state).map(e=>F`<span class="chip activity"
            ><ha-icon class="chip-icon" .icon=${e.ref.icon}></ha-icon>${Dt(`metrics.${e.ref.label}`)}</span
          >`)}renderMetric(e){const t=this.hass?.states[e.entity.entity_id];if(!t||ht(t.state))return;const i=e.over?this.hass?.states[e.over.entity_id]:void 0,n=i&&!ht(i.state)?F`${gi(this.hass,t)}<span class="of">/</span>${gi(this.hass,i)}`:gi(this.hass,t);return yi(e.ref,t,n)}renderLink(e,t){const i=t?.attributes.web_ui_url||e.device.configuration_url||void 0;return function(e){if(!e)return!1;try{const t=new URL(e);return Jt.has(t.protocol)&&""!==t.host}catch{return!1}}(i)?F`
      <a class="link" href=${i} target="_blank" rel="noreferrer noopener" title=${Dt("common.open_link")}>
        <ha-icon icon="mdi:web"></ha-icon>
      </a>
    `:V}renderPower(e){if(!e.powerEntity)return V;const t=this.hass.states[e.powerEntity.entity_id];if(!t)return V;const i="on"===t.state,n=this.pending.has(e.powerEntity.entity_id),s=ht(t.state)||n,o=Dt(n?"common.power_pending":"common.toggle_power");return F`
      <button
        class="power-button ${n?"pending":""}"
        ?disabled=${s}
        title=${o}
        aria-label=${o}
        @click=${t=>this.togglePower(t,e)}
      >
        ${n?F`<span class="spinner" role="progressbar"></span>`:F`<ha-icon icon=${i?"mdi:stop":"mdi:play"}></ha-icon>`}
      </button>
    `}togglePower(e,t){if(e.stopPropagation(),!t.powerEntity)return;const i=t.powerEntity.entity_id;if(this.pending.has(i))return;const n=this.hass.states[i]?.state,s="on"===n;s&&this.config.confirm_stop&&!confirm(Dt("common.confirm_stop","{name}",t.name))||(this.markPending(i,n),this.hass.callService("switch",s?"turn_off":"turn_on",{entity_id:i}).catch(()=>this.clearPending(i)))}markPending(e,t){this.pending=new Map(this.pending).set(e,t??""),this.pendingTimers.start(e,e=>this.clearPending(e))}clearPending(e){if(this.pendingTimers.stop(e),this.pending.has(e)){const t=new Map(this.pending);t.delete(e),this.pending=t}}resumePendingTimers(){for(const e of this.pending.keys())this.pendingTimers.start(e,e=>this.clearPending(e))}configuredAction(e){return"hold"===e?this.config?.hold_action:"double_tap"===e?this.config?.double_tap_action:this.config?.tap_action}handleAction(e,t){if(!this.hass||!this.config||!e.detail?.action)return;const i=this.configuredAction(e.detail.action),n="toggle"===i?.action;if(n&&!t.powerEntity)return;const s=this.placeholderValues(t),o=n?t.powerEntity?.entity_id:t.stateEntity?.entity_id;Pe(this,this.hass,{entity:si(i,s)??o,tap_action:ni(this.config.tap_action,s),hold_action:ni(this.config.hold_action,s),double_tap_action:ni(this.config.double_tap_action,s)},e.detail.action)}placeholderValues(e){return{entity:e.stateEntity?.entity_id,power:e.powerEntity?.entity_id,device_id:e.device.id,name:e.name,kind:e.kind}}static get styles(){return[$i,r`
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

        .separator {
          opacity: 0.6;
        }

        .part {
          white-space: nowrap;
        }

        /* The state word carries the row's tone; the measurements beside it
           stay quiet, so a running row is not a line of green numbers. Rings
           keep their own scale. */
        .state .chip {
          color: var(--secondary-text-color);
        }

        .state .chip.activity {
          color: var(--info-color, var(--primary-color));
        }

        .chip.activity {
          color: var(--info-color, var(--primary-color));
        }

        .of {
          margin: 0 1px;
          opacity: 0.6;
        }

        .kind-heading {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin: 14px 4px 6px;
          font-size: 0.75em;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--secondary-text-color);
        }

        /* Counts read as part of the heading, not as a label of their own: same
         size, no capitals, so "3/4 running" is not shouted. */
        .kind-counts {
          flex: none;
          text-transform: none;
          letter-spacing: normal;
          font-size: 1.1em;
          font-weight: 400;
        }

        .kind-updates {
          color: var(--warning-color, #ffa600);
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
      `]}}e([pe({attribute:!1})],Ii.prototype,"hass",void 0),e([me()],Ii.prototype,"config",void 0),e([me()],Ii.prototype,"devices",void 0),e([me()],Ii.prototype,"entities",void 0),e([me()],Ii.prototype,"icons",void 0),e([me()],Ii.prototype,"pending",void 0),e([me()],Ii.prototype,"expanded",void 0),e([me()],Ii.prototype,"history",void 0),Mi(()=>customElements,"mos-card",Ii);class Fi extends le{constructor(){super(...arguments),this._servers=[],this._computeLabel=e=>Dt(`overview_editor.${e.name}`),this._computeHelper=e=>"navigation_path"===e.name?Dt("overview_editor.navigation_path_hint"):""}setConfig(e){this._config=e}connectedCallback(){super.connectedCallback(),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.(),this._unsubscribe=void 0}willUpdate(e){e.has("hass")&&Rt(this.hass?.locale?.language)}updated(e){e.has("hass")&&this._subscribe()}_subscribe(){!this._unsubscribe&&this.isConnected&&this.hass?.connection&&(this._unsubscribe=Fe(this.hass.connection,e=>{this._servers=We(e)}))}_schema(){return[{name:"title",selector:{text:{}}},{name:"server",selector:{select:{mode:"dropdown",options:[{value:"",label:Dt("editor.all_servers")},...this._servers.map(e=>({value:e.id,label:e.name_by_user||e.name||e.id}))]}}},...Gt.map(e=>({name:e,selector:{boolean:{}}})),{name:"navigation_path",selector:{text:{}}}]}_data(e){const t={title:e.title??"",server:e.server??"",navigation_path:e.navigation_path??""};for(const i of Gt){const n=e[i];t[i]="boolean"==typeof n?n:Ft[i]}return t}render(){return this._config&&this.hass?F`
      <ha-form
        .hass=${this.hass}
        .data=${this._data(this._config)}
        .schema=${this._schema()}
        .computeLabel=${this._computeLabel}
        .computeHelper=${this._computeHelper}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `:V}_valueChanged(e){if(!this._config)return;const t=e.detail.value,i={...this._config,...t};for(const e of Gt)i[e]===Ft[e]&&delete i[e];for(const e of["title","server","navigation_path"])t[e]||delete i[e];Ae(this,"config-changed",{config:i})}static get styles(){return r`
      ha-form {
        display: block;
      }
    `}}e([pe({attribute:!1})],Fi.prototype,"hass",void 0),e([me()],Fi.prototype,"_config",void 0),e([me()],Fi.prototype,"_servers",void 0);const Gi=Mi(()=>customElements,"mos-overview-card-editor",Fi);var Wi=Object.freeze({__proto__:null,MosOverviewCardEditor:Fi,overviewEditorDefined:Gi});const Vi=[{name:"tap_action",default:"more-info"},{name:"hold_action",default:"none"},{name:"double_tap_action",default:"none"}],qi={kinds:"editor.kinds_hint",confirm_stop:"editor.confirm_stop_hint",secondary_info:"editor.secondary_info_hint",show_server_summary:"editor.show_server_summary_hint",show_history:"editor.show_history_hint",show_services:"editor.show_services_hint",show_problem:"editor.show_problem_hint",filter_include:"editor.filter_hint",max_rows:"editor.max_rows_hint",columns:"editor.columns_hint"};class Zi extends le{constructor(){super(...arguments),this._servers=[],this._computeLabel=e=>Dt(`editor.${e.name}`),this._computeHelper=e=>{const t=qi[e.name];return t?Dt(t):""}}setConfig(e){this._config=e}connectedCallback(){super.connectedCallback(),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.(),this._unsubscribe=void 0}willUpdate(e){e.has("hass")&&Rt(this.hass?.locale?.language)}updated(e){e.has("hass")&&this._subscribe()}_subscribe(){!this._unsubscribe&&this.isConnected&&this.hass?.connection&&(this._unsubscribe=Fe(this.hass.connection,e=>{this._servers=We(e)}))}_schema(){return[{name:"title",selector:{text:{}}},{name:"server",selector:{select:{mode:"dropdown",options:[{value:"",label:Dt("editor.all_servers")},...this._servers.map(e=>({value:e.id,label:e.name_by_user||e.name||e.id}))]}}},{name:"kinds",selector:{select:{multiple:!0,options:Ue.map(e=>({value:e,label:Dt(`kinds.${e}`)}))}}},{name:"filter_include",selector:{text:{}}},{name:"filter_exclude",selector:{text:{}}},{name:"max_rows",selector:{number:{min:1,max:100,mode:"box"}}},{name:"columns",selector:{number:{min:1,max:2,mode:"slider"}}},{name:"sort",selector:{select:{mode:"dropdown",options:He.map(e=>({value:e,label:Dt(`editor.sort_${e}`)}))}}},{name:"secondary_info",selector:{select:{mode:"dropdown",options:je.map(e=>({value:e,label:Dt(`editor.secondary_info_${e}`)}))}}},...Kt.map(e=>({name:e,selector:{boolean:{}}})),{name:"actions_note",type:"constant",value:Dt("editor.actions_hint")},...Vi.map(e=>({name:e.name,selector:{ui_action:{default_action:e.default}}}))]}_data(e){const t={title:e.title??"",server:e.server??"",kinds:e.kinds??[...Ue],sort:e.sort??jt.sort,secondary_info:e.secondary_info??jt.secondary_info,columns:e.columns??jt.columns,filter_include:Bt(e.filter?.include),filter_exclude:Bt(e.filter?.exclude),max_rows:e.max_rows};for(const i of Kt){const n=e[i];t[i]="boolean"==typeof n?n:jt[i]}for(const i of Vi)t[i.name]=e[i.name];return t}render(){return this._config&&this.hass?F`
      <ha-form
        .hass=${this.hass}
        .data=${this._data(this._config)}
        .schema=${this._schema()}
        .computeLabel=${this._computeLabel}
        .computeHelper=${this._computeHelper}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `:V}_valueChanged(e){if(!this._config)return;const t=e.detail.value,i={...this._config,...t},n=function(e,t){const i=It(e),n=It(t);if(i.length||n.length)return{...i.length?{include:i}:{},...n.length?{exclude:n}:{}}}(t.filter_include,t.filter_exclude);delete i.filter_include,delete i.filter_exclude,n?i.filter=n:delete i.filter,t.max_rows||delete i.max_rows,Array.isArray(t.kinds)&&!t.kinds.length&&delete i.kinds,t.title||delete i.title,t.server||delete i.server;for(const e of Vi)t[e.name]||delete i[e.name];Ae(this,"config-changed",{config:i})}static get styles(){return r`
      ha-form {
        display: block;
      }
    `}}e([pe({attribute:!1})],Zi.prototype,"hass",void 0),e([me()],Zi.prototype,"_config",void 0),e([me()],Zi.prototype,"_servers",void 0);const Yi=Mi(()=>customElements,"mos-card-editor",Zi);var Xi=Object.freeze({__proto__:null,MosCardEditor:Zi,editorDefined:Yi});export{Ii as MosCard};
