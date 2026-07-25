import * as THREE from 'three';

export type GeneratedKnifeSpec = Readonly<{
  materialChannels: readonly string[];
  environmentAvailable: boolean;
}>;

export function createGeneratedKnife(spec: GeneratedKnifeSpec): THREE.Group {
  const root = new THREE.Group();
  root.name = 'generated-reference-projected-knife';
  const substrate = new THREE.MeshStandardMaterial({ color: '#272a31', metalness: 0.95, roughness: 0.18 });
  substrate.userData.materialChannels = spec.materialChannels;
  const bladeShape = new THREE.Shape();
  bladeShape.moveTo(-0.08, -0.04); bladeShape.lineTo(0.08, -0.04); bladeShape.lineTo(0.82, 0.0);
  bladeShape.lineTo(1.35, 0.17); bladeShape.lineTo(1.55, 0.0); bladeShape.lineTo(1.35, -0.17);
  bladeShape.lineTo(0.82, -0.11); bladeShape.lineTo(0.08, 0.04); bladeShape.lineTo(-0.08, 0.04); bladeShape.closePath();
  const blade = new THREE.Mesh(new THREE.ExtrudeGeometry(bladeShape, { depth: 0.06, bevelEnabled: true, bevelSize: 0.018, bevelThickness: 0.015 }), substrate);
  blade.name = 'blade'; blade.rotation.x = Math.PI / 2; blade.position.set(-0.86, 0.04, -0.03); blade.castShadow = true; root.add(blade);
  const grip = new THREE.Mesh(new THREE.CapsuleGeometry(0.15, 0.62, 12, 24), substrate);
  grip.name = 'handle'; grip.rotation.z = Math.PI / 2; grip.position.set(-1.17, -0.22, 0); grip.scale.set(1, 1, 0.8); grip.castShadow = true; root.add(grip);
  const guard = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.035, 12, 32, Math.PI), substrate);
  guard.name = 'guard'; guard.rotation.z = Math.PI / 2; guard.position.set(-0.75, -0.04, 0); root.add(guard);
  root.rotation.z = -0.12; root.position.y = 0.05;
  root.userData.materialChannels = spec.materialChannels;
  root.userData.environmentAvailable = spec.environmentAvailable;
  return root;
}

export function createGeneratedKnifeEnvironment(): THREE.Group {
  const lights = new THREE.Group();
  const hemi = new THREE.HemisphereLight('#dbe7ff', '#17191d', 2.2); lights.add(hemi);
  const key = new THREE.DirectionalLight('#ffffff', 4); key.position.set(2, 2, 4); key.castShadow = true; lights.add(key);
  const rim = new THREE.DirectionalLight('#5478ff', 3); rim.position.set(-3, 0, -2); lights.add(rim);
  lights.userData.environment = 'runtime-neutral-environment';
  return lights;
}
