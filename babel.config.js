export default function(api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        "module:react-native-dotenv",
        {
          "moduleName": "@env",
          "path": ".env",
          "blacklist": null,
          "whitelist": null,
          "safe": false,
          "allowUndefined": true
        }
      ]
    ]
  };
};
/*Arquivo chave-firebase: o próprio fire te dá código de acesso , é oq sincroniza com o nosso projeto;
babel: é o "motor do .env , ele subistui o @env pelo próprio arquivo, o outro arquivo enve.d só diz para o IDE(VSocde)" que realmente há um caminho para o @env , está mais como uma preocaução*/