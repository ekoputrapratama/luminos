class Observable {

  static from(value){
    let instance = new Observable();
    instance.value = value;
    return instance;
  }

  constructor() {
    this.observers = [];
  }

  subscribe(f) {
    this.observers.push(f);
  }

  unsubscribe(f) {
    this.observers = this.observers.filter(subscriber => subscriber !== f);
  }

  notify(data) {
    this.value = data;
    this.observers.forEach(observer => observer(data));
  }
}
