export const API=import.meta.env.VITE_API_URL||"http://localhost:8000";

export const money=n=>Number(n||0).toLocaleString("pt-BR",{
  style:"currency",
  currency:"BRL"
});

export const blankProduct={
  name:"",
  code:"",
  category:"Espetos",
  description:"",
  image_url:"",
  cost:0,
  price:0,
  stock:0,
  min_stock:10,
  unit:"un",
  sector:"Churrasqueira",
  printer:"Nenhuma",
  track_stock:true,
  active:true
};
