import typescript from '@rollup/plugin-typescript';
import commonjs from '@rollup/plugin-commonjs';
import nodeResolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';
import json from '@rollup/plugin-json';

// Production only. The dev server lives in rollup.config.dev.js, which is what
// `yarn start` runs; this config is only ever invoked as a plain `rollup -c`,
// so the ROLLUP_WATCH branch that used to sit here could never be reached.
const plugins = [nodeResolve(), commonjs(), typescript(), json(), terser()];

const onwarn = (warning, warn) => {
  if (warning.code === 'THIS_IS_UNDEFINED' && warning.id?.includes('/node_modules/')) {
    return;
  }

  warn(warning);
};

export default [
  {
    input: 'src/mos-card.ts',
    output: {
      file: '../custom_components/mos/www/mos-card.js',
      format: 'es',
      inlineDynamicImports: true,
    },
    plugins,
    onwarn,
  },
];
